import os
import logging
from flask import Flask, render_template, request, jsonify, make_response
from scraper import TGSPDCLScraper
import pandas as pd
from io import BytesIO
import time
from models import db, ServiceNumber, BillHistory, ScrapingLog
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
else:
    # Fallback for development without database
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bills.db"
    
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Main page with service number input form"""
    return render_template('index.html')

def get_or_create_service_number(service_number):
    """Get or create a service number entry in the database"""
    service_entry = ServiceNumber.query.filter_by(service_number=service_number).first()
    if not service_entry:
        service_entry = ServiceNumber(service_number=service_number)
        db.session.add(service_entry)
        db.session.commit()
    return service_entry

def save_bill_to_database(service_entry, bill_data, source_website):
    """Save a bill to the database"""
    try:
        # Parse date if available
        bill_date = None
        if bill_data.get('date'):
            try:
                # Try different date formats
                date_str = bill_data['date']
                for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d-%m-%y']:
                    try:
                        bill_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
            except:
                pass
        
        # Check if bill already exists
        existing_bill = BillHistory.query.filter_by(
            service_number_id=service_entry.id,
            bill_date=bill_date,
            amount=bill_data.get('amount')
        ).first()
        
        if not existing_bill:
            new_bill = BillHistory(
                service_number_id=service_entry.id,
                bill_number=bill_data.get('bill_number'),
                bill_date=bill_date,
                amount=bill_data.get('amount'),
                status=bill_data.get('status'),
                source_website=source_website,
                raw_data=json.dumps(bill_data)
            )
            db.session.add(new_bill)
            return True
        return False
    except Exception as e:
        logger.error(f"Error saving bill to database: {str(e)}")
        return False

@app.route('/scrape', methods=['POST'])
def scrape_bills():
    """Scrape bill history for provided service numbers"""
    try:
        service_numbers = request.form.get('service_numbers', '').strip()
        
        if not service_numbers:
            return render_template('results.html', 
                                 error="Please provide at least one service number")
        
        # Parse service numbers from textarea (split by newlines and commas)
        numbers = []
        for line in service_numbers.split('\n'):
            line = line.strip()
            if line:
                # Split by comma if multiple numbers on same line
                numbers.extend([num.strip() for num in line.split(',') if num.strip()])
        
        if not numbers:
            return render_template('results.html', 
                                 error="Please provide valid service numbers")
        
        # Initialize scraper
        scraper = TGSPDCLScraper()
        
        # Scrape data for each service number
        results = {}
        errors = {}
        
        for service_number in numbers:
            logger.info(f"Scraping data for service number: {service_number}")
            start_time = time.time()
            
            try:
                # Get or create service number in database
                service_entry = get_or_create_service_number(service_number)
                
                # Check if we have recent data (within last 6 hours)
                recent_cutoff = datetime.utcnow() - timedelta(hours=6)
                recent_bills = BillHistory.query.filter(
                    BillHistory.service_number_id == service_entry.id,
                    BillHistory.created_at > recent_cutoff
                ).all()
                
                # If we have recent data, use it instead of scraping
                if recent_bills and service_entry.last_scraped and service_entry.last_scraped > recent_cutoff:
                    logger.info(f"Using cached data for service number: {service_number}")
                    all_bills = BillHistory.query.filter_by(service_number_id=service_entry.id).order_by(BillHistory.bill_date.desc()).all()
                    results[service_number] = [bill.to_dict() for bill in all_bills]
                else:
                    # Scrape new data
                    bill_history = scraper.get_bill_history(service_number)
                    
                    if bill_history:
                        # Save bills to database
                        new_bills_count = 0
                        for bill in bill_history:
                            if save_bill_to_database(service_entry, bill, bill.get('source', 'scraped')):
                                new_bills_count += 1
                        
                        # Update last scraped time
                        service_entry.last_scraped = datetime.utcnow()
                        db.session.commit()
                        
                        # Get all bills from database for this service number
                        all_bills = BillHistory.query.filter_by(service_number_id=service_entry.id).order_by(BillHistory.bill_date.desc()).all()
                        results[service_number] = [bill.to_dict() for bill in all_bills]
                        
                        # Log scraping activity
                        log_entry = ScrapingLog(
                            service_number=service_number,
                            status='success',
                            bills_found=len(bill_history),
                            scraping_duration=time.time() - start_time
                        )
                        db.session.add(log_entry)
                        db.session.commit()
                        
                        logger.info(f"Saved {new_bills_count} new bills for service number: {service_number}")
                    else:
                        errors[service_number] = "No bill history found"
                        
                        # Log error
                        log_entry = ScrapingLog(
                            service_number=service_number,
                            status='no_data',
                            bills_found=0,
                            scraping_duration=time.time() - start_time
                        )
                        db.session.add(log_entry)
                        db.session.commit()
                        
            except Exception as e:
                logger.error(f"Error scraping {service_number}: {str(e)}")
                errors[service_number] = str(e)
                
                # Log error
                log_entry = ScrapingLog(
                    service_number=service_number,
                    status='error',
                    error_message=str(e),
                    bills_found=0,
                    scraping_duration=time.time() - start_time
                )
                db.session.add(log_entry)
                db.session.commit()
            
            # Add delay between requests to be respectful
            time.sleep(1)
        
        return render_template('results.html', 
                             results=results, 
                             errors=errors,
                             service_numbers=numbers)
    
    except Exception as e:
        logger.error(f"Error in scrape_bills: {str(e)}")
        return render_template('results.html', 
                             error=f"An error occurred: {str(e)}")

@app.route('/export/<service_number>')
def export_data(service_number):
    """Export bill history data to Excel from database"""
    try:
        # Get service number from database
        service_entry = ServiceNumber.query.filter_by(service_number=service_number).first()
        
        if not service_entry:
            return jsonify({'error': 'Service number not found in database'}), 404
        
        # Get all bills for this service number from database
        bills = BillHistory.query.filter_by(service_number_id=service_entry.id).order_by(BillHistory.bill_date.desc()).all()
        
        if not bills:
            return jsonify({'error': 'No bill history found for this service number'}), 404
        
        # Convert to DataFrame
        bill_data = []
        for bill in bills:
            bill_data.append({
                'Service Number': service_number,
                'Bill Number': bill.bill_number or 'N/A',
                'Bill Date': bill.bill_date.strftime('%Y-%m-%d') if bill.bill_date else 'N/A',
                'Amount': bill.amount or 'N/A',
                'Status': bill.status or 'N/A',
                'Source Website': bill.source_website or 'N/A',
                'Scraped On': bill.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        df = pd.DataFrame(bill_data)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=f'Bills_{service_number}', index=False)
        
        output.seek(0)
        
        # Create response
        response = make_response(output.read())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=bills_{service_number}.xlsx'
        
        return response
    
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/service-numbers')
def get_service_numbers():
    """Get all service numbers from database"""
    try:
        service_numbers = ServiceNumber.query.all()
        return jsonify([{
            'service_number': sn.service_number,
            'created_at': sn.created_at.isoformat(),
            'last_scraped': sn.last_scraped.isoformat() if sn.last_scraped else None,
            'bill_count': len(sn.bills)
        } for sn in service_numbers])
    except Exception as e:
        logger.error(f"Error fetching service numbers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bills/<service_number>')
def get_bills_api(service_number):
    """Get bills for a service number via API"""
    try:
        service_entry = ServiceNumber.query.filter_by(service_number=service_number).first()
        if not service_entry:
            return jsonify({'error': 'Service number not found'}), 404
        
        bills = BillHistory.query.filter_by(service_number_id=service_entry.id).order_by(BillHistory.bill_date.desc()).all()
        return jsonify([bill.to_dict() for bill in bills])
    except Exception as e:
        logger.error(f"Error fetching bills: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Admin dashboard showing database statistics"""
    try:
        # Get statistics
        total_service_numbers = ServiceNumber.query.count()
        total_bills = BillHistory.query.count()
        recent_scrapes = ScrapingLog.query.order_by(ScrapingLog.created_at.desc()).limit(10).all()
        
        # Get service numbers with bill counts
        service_numbers = db.session.query(
            ServiceNumber.service_number,
            ServiceNumber.last_scraped,
            db.func.count(BillHistory.id).label('bill_count')
        ).outerjoin(BillHistory).group_by(ServiceNumber.id).all()
        
        return render_template('dashboard.html',
                             total_service_numbers=total_service_numbers,
                             total_bills=total_bills,
                             recent_scrapes=recent_scrapes,
                             service_numbers=service_numbers)
    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}")
        return render_template('dashboard.html', error=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
