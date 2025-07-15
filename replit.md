# TGSPDCL Bill History Scraper

## Overview

This is a Flask-based web application that scrapes electricity bill payment history for TGSPDCL (Telangana State Southern Power Distribution Company Limited) service numbers from official websites. The application provides a clean web interface, database storage, caching, and export functionality.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Technology**: Server-side rendered HTML templates using Flask's Jinja2 templating
- **UI Framework**: Bootstrap 5 with custom CSS for styling
- **Icons**: Feather icons for UI elements
- **Pages**: 
  - Main form for service number input (`index.html`)
  - Results display page (`results.html`)
  - Database dashboard (`dashboard.html`)

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Application Structure**: 
  - `main.py`: Entry point
  - `app.py`: Flask application configuration and routes
  - `scraper.py`: Web scraping logic
  - `models.py`: Database models using SQLAlchemy ORM
- **Design Pattern**: MVC pattern with clear separation of concerns

### Data Storage Solutions
- **Primary Database**: PostgreSQL (production)
- **Fallback Database**: SQLite (development/local)
- **ORM**: SQLAlchemy with Flask-SQLAlchemy extension
- **Models**:
  - `ServiceNumber`: Stores service numbers and metadata
  - `BillHistory`: Stores scraped bill data
  - `ScrapingLog`: Tracks scraping activities
- **Caching Strategy**: Smart caching to avoid re-scraping recent data

## Key Components

### Web Scraping Engine (`scraper.py`)
- **Purpose**: Extracts bill history from multiple TGSPDCL websites
- **Approach**: Multi-source scraping with fallback mechanisms
- **Features**:
  - Handles multiple target websites
  - Request session management with proper headers
  - Error handling and retry logic
  - Data deduplication and sorting

### Database Models (`models.py`)
- **ServiceNumber Model**: Tracks service numbers and last scraping timestamp
- **BillHistory Model**: Stores individual bill records with unique constraints
- **Relationships**: One-to-many relationship between ServiceNumber and BillHistory

### Web Application (`app.py`)
- **Route Handlers**: Main form, scraping endpoint, results display, dashboard
- **Database Integration**: SQLAlchemy session management
- **Export Functionality**: Excel export using pandas
- **Error Handling**: Comprehensive error handling and logging

## Data Flow

1. **User Input**: Service numbers entered through web form
2. **Validation**: Input validation and parsing (comma-separated or line-separated)
3. **Cache Check**: Database lookup to avoid recent re-scraping
4. **Web Scraping**: Multi-website scraping with error handling
5. **Data Storage**: Parsed bill data stored in PostgreSQL/SQLite
6. **Response**: Results displayed with export options
7. **Dashboard**: Database statistics and management interface

## External Dependencies

### Web Scraping
- **requests**: HTTP client for web requests
- **beautifulsoup4**: HTML parsing and data extraction
- **trafilatura**: Text extraction from web pages

### Data Processing
- **pandas**: Data manipulation and Excel export
- **openpyxl**: Excel file format support

### Database
- **psycopg2-binary**: PostgreSQL adapter
- **Flask-SQLAlchemy**: ORM integration

### Web Framework
- **Flask**: Core web framework
- **gunicorn**: WSGI HTTP server for production

## Deployment Strategy

### Development
- **Local Server**: Flask development server (`python main.py`)
- **Database**: SQLite fallback for local development
- **Configuration**: Environment variables for database URL and session secret

### Production
- **WSGI Server**: Gunicorn with recommended settings
- **Database**: PostgreSQL with connection pooling
- **Environment Variables**:
  - `DATABASE_URL`: PostgreSQL connection string
  - `SESSION_SECRET`: Flask session security key
- **Scalability**: Gunicorn with `--reuse-port` and `--reload` options

### Key Design Decisions

1. **Multi-Source Scraping**: Prioritizes reliability by scraping multiple official websites
2. **Smart Caching**: Prevents unnecessary re-scraping of recent data to reduce server load
3. **Database Flexibility**: Supports both PostgreSQL (production) and SQLite (development)
4. **Error Resilience**: Continues processing even if individual websites fail
5. **Export Functionality**: Provides Excel export for data analysis and reporting
6. **Logging**: Comprehensive logging for debugging and monitoring scraping activities

### Security Considerations
- Uses proper user agents to avoid blocking
- Implements request timeouts and session management
- Stores sensitive configuration in environment variables
- Includes unique constraints to prevent duplicate data storage