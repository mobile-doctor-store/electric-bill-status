from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import json

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class ServiceNumber(db.Model):
    __tablename__ = 'service_numbers'
    
    id = db.Column(db.Integer, primary_key=True)
    service_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_scraped = db.Column(db.DateTime)
    
    # Relationship to bills
    bills = db.relationship('BillHistory', backref='service_account', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ServiceNumber {self.service_number}>'

class BillHistory(db.Model):
    __tablename__ = 'bill_history'
    
    id = db.Column(db.Integer, primary_key=True)
    service_number_id = db.Column(db.Integer, db.ForeignKey('service_numbers.id'), nullable=False)
    
    # Bill details
    bill_number = db.Column(db.String(50))
    bill_date = db.Column(db.Date)
    amount = db.Column(db.String(20))
    status = db.Column(db.String(20))
    
    # Metadata
    source_website = db.Column(db.String(200))
    raw_data = db.Column(db.Text)  # JSON string of original scraped data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate bills
    __table_args__ = (
        db.UniqueConstraint('service_number_id', 'bill_date', 'amount', name='unique_bill'),
    )
    
    def to_dict(self):
        """Convert bill to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'service_number': self.service_account.service_number,
            'bill_number': self.bill_number,
            'date': self.bill_date.isoformat() if self.bill_date else None,
            'amount': self.amount,
            'status': self.status,
            'source': self.source_website,
            'raw_data': json.loads(self.raw_data) if self.raw_data else None
        }
    
    def __repr__(self):
        return f'<BillHistory {self.bill_number} - {self.amount}>'

class ScrapingLog(db.Model):
    __tablename__ = 'scraping_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    service_number = db.Column(db.String(20), nullable=False)
    website = db.Column(db.String(200))
    status = db.Column(db.String(20))  # success, error, timeout
    error_message = db.Column(db.Text)
    bills_found = db.Column(db.Integer, default=0)
    scraping_duration = db.Column(db.Float)  # seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ScrapingLog {self.service_number} - {self.status}>'