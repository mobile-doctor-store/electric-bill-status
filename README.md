# TGSPDCL Bill History Scraper

A simple Flask web application that retrieves real-time electricity bill payment history for TGSPDCL (Telangana State Southern Power Distribution Company Limited) service numbers.

## Features

- Clean, simple web interface
- Real-time data fetching from official TGSPDCL websites
- PostgreSQL database storage for bill history
- Smart caching system (avoids re-scraping recent data)
- Support for multiple service numbers
- Excel export functionality from database
- Database dashboard with statistics
- API endpoints for programmatic access
- Scraping activity logging

## Quick Start

1. Install Python 3.11 or higher
2. Install required packages:
   ```bash
   pip install flask requests beautifulsoup4 pandas gunicorn flask-sqlalchemy psycopg2-binary
   ```
3. Set up PostgreSQL database (optional - uses SQLite fallback):
   ```bash
   export DATABASE_URL="postgresql://username:password@localhost/tgspdcl"
   ```
4. Run the application:
   ```bash
   python main.py
   ```
5. Open your browser to `http://localhost:5000`

## Deployment

### Using Gunicorn (Recommended)
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Environment Variables
- `SESSION_SECRET`: Set a secure secret key for Flask sessions

## Usage

1. Enter TGSPDCL service numbers in the input field
2. Click "Get Bill History" 
3. View results in the web interface
4. Export data to Excel if needed
5. Visit `/dashboard` to view database statistics and manage data

## API Endpoints

- `GET /api/service-numbers` - Get all service numbers
- `GET /api/bills/<service_number>` - Get bills for a specific service number
- `GET /dashboard` - Database statistics dashboard

## Files Structure

- `main.py` - Application entry point
- `app.py` - Flask application and routes
- `models.py` - Database models (ServiceNumber, BillHistory, ScrapingLog)
- `scraper.py` - Web scraping logic for TGSPDCL websites
- `templates/` - HTML templates (index, results, dashboard)
- `static/` - CSS styles

## Target Websites

The scraper fetches data from these official TGSPDCL sources:
- tgsouthernpower.org/HtCurrentMonthbillhistory
- webportal.tgsouthernpower.org/TGSPDCL/Billinginfo/Billinginfo.jsp
- tgsouthernpower.org
- billdesk.com (TGSPDCL payment gateway)

## Deployment

### For Heroku/Railway/Render (Recommended)
1. Upload these files to GitHub:
   - `main.py`, `app.py`, `models.py`, `scraper.py`
   - `templates/` folder
   - `static/` folder
   - `requirements-deploy.txt` (rename to `requirements.txt`)
   - `Procfile`
   - `runtime.txt`
   - `README.md`
   - `.gitignore`

2. Set environment variables:
   - `DATABASE_URL`: PostgreSQL connection string
   - `SESSION_SECRET`: Random secret key

### For Vercel (Limited PostgreSQL support)
1. Upload the same files plus `vercel.json`
2. Note: Vercel has limited database support for Python apps

### Files NOT to upload:
- `.replit`, `uv.lock`, `pyproject.toml` (Replit-specific)
- `__pycache__/`, `*.pyc` (Python cache files)
- `.pythonlibs/`, `.cache/`, `.local/`, `.upm/` (local data)

## Note

This tool fetches real-time data from official TGSPDCL websites. Processing may take a few minutes depending on website response times.