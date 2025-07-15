import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, urlparse
import json

logger = logging.getLogger(__name__)

class TGSPDCLScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Target websites - prioritize most reliable sources
        self.websites = [
            'https://tgsouthernpower.org/HtCurrentMonthbillhistory',
            'https://webportal.tgsouthernpower.org/TGSPDCL/Billinginfo/Billinginfo.jsp',
            'https://tgsouthernpower.org/',
            'https://www.billdesk.com/pgidsk/pgmerc/tsspdclpgi/TSSPDCLPGIDetails.jsp'
        ]
        
        # Configure session with timeout and retries
        self.session.timeout = 15
        
    def get_bill_history(self, service_number):
        """
        Scrape bill history for a given service number from multiple websites
        """
        all_bills = []
        
        for website in self.websites:
            try:
                logger.info(f"Scraping {website} for service number {service_number}")
                bills = self._scrape_website(website, service_number)
                if bills:
                    all_bills.extend(bills)
                    
            except Exception as e:
                logger.error(f"Error scraping {website}: {str(e)}")
                continue
            
            # Add delay between website requests
            time.sleep(1)
        
        # Remove duplicates and sort by date
        unique_bills = self._remove_duplicates(all_bills)
        
        # Filter to last 20 months
        filtered_bills = self._filter_last_20_months(unique_bills)
        
        return filtered_bills
    
    def _scrape_website(self, url, service_number):
        """
        Scrape a specific website for bill history
        """
        try:
            if 'tgsouthernpower.org' in url:
                return self._scrape_tgsouthernpower(url, service_number)
            elif 'billdesk.com' in url:
                return self._scrape_billdesk(url, service_number)
            elif 'webportal.tgsouthernpower.org' in url:
                return self._scrape_webportal(url, service_number)
            else:
                return self._generic_scrape(url, service_number)
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return []
    
    def _scrape_tgsouthernpower(self, url, service_number):
        """
        Scrape tgsouthernpower.org websites
        """
        bills = []
        
        try:
            # Try to find bill history page or search functionality
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for forms that might accept service numbers
            forms = soup.find_all('form')
            
            for form in forms:
                # Look for input fields that might be for service numbers
                inputs = form.find_all('input')
                for input_field in inputs:
                    if any(keyword in str(input_field).lower() for keyword in 
                          ['service', 'consumer', 'account', 'number']):
                        
                        # Try to submit the form with the service number
                        bills.extend(self._submit_form_and_parse(form, url, service_number))
                        break
            
            # Also try to find direct links to bill history
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if any(keyword in href.lower() for keyword in ['bill', 'history', 'payment']):
                    full_url = urljoin(url, href)
                    bills.extend(self._follow_link_and_search(full_url, service_number))
            
        except Exception as e:
            logger.error(f"Error scraping tgsouthernpower: {str(e)}")
        
        return bills
    
    def _scrape_billdesk(self, url, service_number):
        """
        Scrape billdesk.com for payment history
        """
        bills = []
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for payment gateway forms
            forms = soup.find_all('form')
            
            for form in forms:
                # Try to find service number input
                inputs = form.find_all('input')
                service_input = None
                
                for input_field in inputs:
                    if any(keyword in str(input_field).lower() for keyword in 
                          ['service', 'consumer', 'account']):
                        service_input = input_field
                        break
                
                if service_input:
                    bills.extend(self._submit_billdesk_form(form, url, service_number))
            
        except Exception as e:
            logger.error(f"Error scraping billdesk: {str(e)}")
        
        return bills
    
    def _scrape_webportal(self, url, service_number):
        """
        Scrape webportal.tgsouthernpower.org
        """
        bills = []
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for billing information forms
            forms = soup.find_all('form')
            
            for form in forms:
                if 'billing' in str(form).lower():
                    bills.extend(self._submit_form_and_parse(form, url, service_number))
            
        except Exception as e:
            logger.error(f"Error scraping webportal: {str(e)}")
        
        return bills
    
    def _generic_scrape(self, url, service_number):
        """
        Generic scraping method for any website
        """
        bills = []
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for tables that might contain bill information
            tables = soup.find_all('table')
            
            for table in tables:
                if any(keyword in str(table).lower() for keyword in 
                      ['bill', 'payment', 'amount', 'due']):
                    bills.extend(self._parse_bill_table(table, service_number))
            
        except Exception as e:
            logger.error(f"Error in generic scrape: {str(e)}")
        
        return bills
    
    def _submit_form_and_parse(self, form, base_url, service_number):
        """
        Submit a form with service number and parse results
        """
        bills = []
        
        try:
            # Extract form data
            form_data = {}
            action = form.get('action', '')
            method = form.get('method', 'GET').upper()
            
            if not action:
                return bills
                
            full_action_url = urljoin(base_url, action)
            
            # Fill form inputs
            inputs = form.find_all('input')
            for input_field in inputs:
                name = input_field.get('name')
                if name:
                    if any(keyword in name.lower() for keyword in 
                          ['service', 'consumer', 'account', 'number']):
                        form_data[name] = service_number
                    else:
                        form_data[name] = input_field.get('value', '')
            
            # Submit form
            if method == 'POST':
                response = self.session.post(full_action_url, data=form_data)
            else:
                response = self.session.get(full_action_url, params=form_data)
            
            response.raise_for_status()
            
            # Parse response for bill information
            soup = BeautifulSoup(response.content, 'html.parser')
            bills.extend(self._parse_bill_response(soup, service_number))
            
        except Exception as e:
            logger.error(f"Error submitting form: {str(e)}")
        
        return bills
    
    def _submit_billdesk_form(self, form, base_url, service_number):
        """
        Special handling for billdesk forms
        """
        bills = []
        
        try:
            # Billdesk might have specific form handling
            form_data = {'consumerNumber': service_number}
            
            action = form.get('action', '')
            if action:
                full_url = urljoin(base_url, action)
                response = self.session.post(full_url, data=form_data)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                bills.extend(self._parse_bill_response(soup, service_number))
            
        except Exception as e:
            logger.error(f"Error with billdesk form: {str(e)}")
        
        return bills
    
    def _follow_link_and_search(self, url, service_number):
        """
        Follow a link and search for bill information
        """
        bills = []
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for forms to submit service number
            forms = soup.find_all('form')
            for form in forms:
                bills.extend(self._submit_form_and_parse(form, url, service_number))
            
        except Exception as e:
            logger.error(f"Error following link {url}: {str(e)}")
        
        return bills
    
    def _parse_bill_response(self, soup, service_number):
        """
        Parse HTML response for bill information
        """
        bills = []
        
        try:
            # Look for tables with bill data
            tables = soup.find_all('table')
            
            for table in tables:
                bills.extend(self._parse_bill_table(table, service_number))
            
            # Look for div elements that might contain bill info
            divs = soup.find_all('div')
            for div in divs:
                if any(keyword in str(div).lower() for keyword in 
                      ['bill', 'amount', 'due', 'payment']):
                    bills.extend(self._parse_bill_div(div, service_number))
            
        except Exception as e:
            logger.error(f"Error parsing bill response: {str(e)}")
        
        return bills
    
    def _parse_bill_table(self, table, service_number):
        """
        Parse a table for bill information
        """
        bills = []
        
        try:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 3:  # Assume at least 3 columns for meaningful data
                    bill_data = {}
                    
                    # Extract text from cells
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # Try to identify bill information patterns
                    for i, text in enumerate(cell_texts):
                        # Look for dates
                        if self._is_date(text):
                            bill_data['date'] = text
                        
                        # Look for amounts
                        elif self._is_amount(text):
                            bill_data['amount'] = text
                        
                        # Look for bill numbers
                        elif self._is_bill_number(text):
                            bill_data['bill_number'] = text
                        
                        # Look for status
                        elif any(status in text.lower() for status in ['paid', 'unpaid', 'due']):
                            bill_data['status'] = text
                    
                    if bill_data and ('date' in bill_data or 'amount' in bill_data):
                        bill_data['service_number'] = service_number
                        bill_data['source'] = 'scraped'
                        bills.append(bill_data)
            
        except Exception as e:
            logger.error(f"Error parsing bill table: {str(e)}")
        
        return bills
    
    def _parse_bill_div(self, div, service_number):
        """
        Parse a div element for bill information
        """
        bills = []
        
        try:
            text = div.get_text(strip=True)
            
            # Look for patterns in the text
            if self._contains_bill_info(text):
                bill_data = {
                    'service_number': service_number,
                    'source': 'scraped',
                    'raw_text': text
                }
                
                # Try to extract specific information
                date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
                if date_match:
                    bill_data['date'] = date_match.group()
                
                amount_match = re.search(r'₹?\s*(\d+(?:,\d+)*(?:\.\d{2})?)', text)
                if amount_match:
                    bill_data['amount'] = amount_match.group()
                
                bills.append(bill_data)
            
        except Exception as e:
            logger.error(f"Error parsing bill div: {str(e)}")
        
        return bills
    
    def _is_date(self, text):
        """Check if text looks like a date"""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}-\w{3}-\d{2,4}',
            r'\w{3}\s+\d{1,2},?\s+\d{4}'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _is_amount(self, text):
        """Check if text looks like a monetary amount"""
        amount_patterns = [
            r'₹\s*\d+(?:,\d+)*(?:\.\d{2})?',
            r'\d+(?:,\d+)*(?:\.\d{2})?\s*₹',
            r'Rs\.?\s*\d+(?:,\d+)*(?:\.\d{2})?'
        ]
        
        for pattern in amount_patterns:
            if re.search(pattern, text):
                return True
        
        # Also check for plain numbers that might be amounts
        if re.search(r'\d+(?:,\d+)*(?:\.\d{2})?', text) and len(text) <= 20:
            return True
        
        return False
    
    def _is_bill_number(self, text):
        """Check if text looks like a bill number"""
        # Bill numbers are usually alphanumeric with specific patterns
        return re.search(r'[A-Z0-9]{6,}', text) is not None
    
    def _contains_bill_info(self, text):
        """Check if text contains bill-related information"""
        keywords = ['bill', 'amount', 'due', 'payment', 'paid', 'outstanding', 'balance']
        return any(keyword in text.lower() for keyword in keywords)
    
    def _remove_duplicates(self, bills):
        """Remove duplicate bills based on date and amount"""
        unique_bills = []
        seen = set()
        
        for bill in bills:
            # Create a key for uniqueness check
            key = (bill.get('date', ''), bill.get('amount', ''), bill.get('service_number', ''))
            
            if key not in seen:
                seen.add(key)
                unique_bills.append(bill)
        
        return unique_bills
    
    def _filter_last_20_months(self, bills):
        """Filter bills to last 20 months"""
        try:
            # Calculate date 20 months ago
            current_date = datetime.now()
            twenty_months_ago = current_date - timedelta(days=20*30)  # Approximate
            
            filtered_bills = []
            
            for bill in bills:
                bill_date = self._parse_date(bill.get('date', ''))
                
                if bill_date and bill_date >= twenty_months_ago:
                    filtered_bills.append(bill)
                elif not bill_date:
                    # If we can't parse the date, include it anyway
                    filtered_bills.append(bill)
            
            # Sort by date (most recent first)
            filtered_bills.sort(key=lambda x: self._parse_date(x.get('date', '')) or datetime.min, reverse=True)
            
            return filtered_bills
        
        except Exception as e:
            logger.error(f"Error filtering bills: {str(e)}")
            return bills
    
    def _parse_date(self, date_str):
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        date_formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d/%m/%y',
            '%d-%m-%y',
            '%Y-%m-%d',
            '%d-%b-%Y',
            '%d %b %Y',
            '%b %d, %Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
