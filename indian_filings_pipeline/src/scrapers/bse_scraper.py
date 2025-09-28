"""
BSE (Bombay Stock Exchange) scraper for company filings
"""
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from src.database.models import Company
from src.utils.helpers import extract_year_from_text, classify_document_type
from config.settings import settings

logger = logging.getLogger(__name__)

class BSEScraper(BaseScraper):
    """Scraper for BSE India website"""
    
    def __init__(self):
        super().__init__("bse_scraper")
        self.base_url = settings.BSE_BASE_URL
        
        # BSE specific URL patterns
        self.company_page_url = f"{self.base_url}/stock-share-price"
        self.announcements_url = f"{self.base_url}/corporates/ann.aspx"
        self.results_url = f"{self.base_url}/corporates/Results.aspx"
        
        # Document type patterns for BSE
        self.doc_patterns = {
            'annual_report': ['annual report', 'annual', 'yearly report', 'ar'],
            'quarterly_result': ['quarterly', 'quarter', 'q1', 'q2', 'q3', 'q4', 'result', 'financial result'],
            'presentation': ['presentation', 'investor', 'ppt', 'slides', 'earnings call', 'concall'],
            'board_meeting': ['board meeting', 'board', 'meeting outcome', 'intimation'],
            'shareholding': ['shareholding pattern', 'shareholding', 'shares holding'],
            'other': ['notice', 'announcement', 'disclosure', 'intimation', 'outcome']
        }
    
    def discover_documents(self, company: Company) -> List[Dict]:
        """Discover available documents for a company from BSE"""
        documents = []
        
        try:
            # Get company symbol safely for logging
            try:
                company_symbol = company.symbol
            except Exception as e:
                logger.error(f"Unable to access company symbol: {e}")
                return documents
            
            # Get announcements
            announcement_docs = self._get_announcements(company)
            documents.extend(announcement_docs)
            
            # Get financial results
            result_docs = self._get_financial_results(company)
            documents.extend(result_docs)
            
            self.stats['documents_found'] = len(documents)
            logger.info(f"Found {len(documents)} documents for {company_symbol} on BSE")
            
        except Exception as e:
            logger.error(f"Error discovering documents: {e}")
            self.stats['errors'].append(f"Discovery error: {str(e)}")
        
        return documents
    
    def _get_announcements(self, company: Company) -> List[Dict]:
        """Get company announcements from BSE"""
        documents = []
        
        try:
            # Get company code safely
            try:
                bse_code = company.bse_code
                company_symbol = company.symbol
            except Exception as e:
                logger.error(f"Unable to access company attributes: {e}")
                return documents
            
            # BSE announcements page with company filter
            params = {
                'scripcd': bse_code,
                'myDate1': '',  # Will be set for date range
                'myDate2': '',
                'categoryid': '-1',  # All categories
                'subcatid': '-1'     # All subcategories
            }
            
            response = self.make_request(self.announcements_url, params=params)
            if not response:
                return documents
            
            soup = self.parse_html(response)
            if not soup:
                return documents
            
            # Parse announcements table
            documents = self._parse_announcements_table(soup, company)
            
        except Exception as e:
            logger.error(f"Error fetching announcements for {company_symbol}: {e}")
        
        return documents
    
    def _get_financial_results(self, company: Company) -> List[Dict]:
        """Get financial results from BSE"""
        documents = []
        
        try:
            # Get company code safely
            try:
                bse_code = company.bse_code
                company_symbol = company.symbol
            except Exception as e:
                logger.error(f"Unable to access company attributes: {e}")
                return documents
            
            # BSE results page with company filter
            params = {
                'scripcd': bse_code,
                'from': '',  # Date from
                'to': '',    # Date to
            }
            
            response = self.make_request(self.results_url, params=params)
            if not response:
                return documents
            
            soup = self.parse_html(response)
            if not soup:
                return documents
            
            # Parse results table
            documents = self._parse_results_table(soup, company)
            
        except Exception as e:
            logger.error(f"Error fetching financial results for {company_symbol}: {e}")
        
        return documents
    
    def _parse_announcements_table(self, soup, company: Company) -> List[Dict]:
        """Parse BSE announcements table"""
        documents = []
        
        try:
            # Find the announcements table (structure may vary)
            table = soup.find('table', {'id': 'ContentPlaceHolder1_gvData'})
            if not table:
                # Try alternative table selectors
                table = soup.find('table', class_='TTData')
            
            if not table:
                logger.warning(f"No announcements table found for {company.symbol}")
                return documents
            
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 4:
                        continue
                    
                    # Extract information from table cells
                    # BSE table structure: Date | Category | Subject | PDF Link
                    date_cell = cells[0].get_text(strip=True)
                    category_cell = cells[1].get_text(strip=True)
                    subject_cell = cells[2].get_text(strip=True)
                    
                    # Find PDF link
                    pdf_link = None
                    link_cell = cells[3] if len(cells) > 3 else cells[2]
                    link_tag = link_cell.find('a')
                    if link_tag and link_tag.get('href'):
                        pdf_link = urljoin(self.base_url, link_tag['href'])
                    
                    if not pdf_link:
                        continue
                    
                    # Parse document information
                    doc_info = self._parse_announcement_row(
                        date_cell, category_cell, subject_cell, pdf_link, company
                    )
                    
                    if doc_info:
                        documents.append(doc_info)
                
                except Exception as e:
                    logger.debug(f"Error parsing announcement row: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing announcements table: {e}")
        
        return documents
    
    def _parse_results_table(self, soup, company: Company) -> List[Dict]:
        """Parse BSE financial results table"""
        documents = []
        
        try:
            # Find the results table
            table = soup.find('table', {'id': 'ContentPlaceHolder1_gvData'})
            if not table:
                table = soup.find('table', class_='TTData')
            
            if not table:
                logger.warning(f"No results table found for {company.symbol}")
                return documents
            
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 3:
                        continue
                    
                    # Extract information from table cells
                    # BSE results table structure: Date | Period | PDF Link
                    date_cell = cells[0].get_text(strip=True)
                    period_cell = cells[1].get_text(strip=True)
                    
                    # Find PDF link
                    pdf_link = None
                    link_cell = cells[2] if len(cells) > 2 else cells[1]
                    link_tag = link_cell.find('a')
                    if link_tag and link_tag.get('href'):
                        pdf_link = urljoin(self.base_url, link_tag['href'])
                    
                    if not pdf_link:
                        continue
                    
                    # Parse document information
                    doc_info = self._parse_result_row(
                        date_cell, period_cell, pdf_link, company
                    )
                    
                    if doc_info:
                        documents.append(doc_info)
                
                except Exception as e:
                    logger.debug(f"Error parsing result row: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing results table: {e}")
        
        return documents
    
    def _parse_announcement_row(self, date_str: str, category: str, 
                               subject: str, pdf_link: str, company: Company) -> Optional[Dict]:
        """Parse individual announcement row"""
        try:
            # Classify document type
            combined_text = f"{category} {subject}".lower()
            doc_type = classify_document_type(combined_text, self.doc_patterns)
            
            # Extract year and period information
            year = extract_year_from_text(combined_text + ' ' + date_str)
            quarter = self._extract_quarter(combined_text)
            
            # Parse date
            published_date = None
            if date_str:
                published_date = self._parse_bse_date(date_str)
            
            # Generate period string
            period = None
            if quarter and year:
                period = f"{quarter}FY{year}"
            elif year:
                period = f"FY{year}"
            
            return {
                'title': subject,
                'url': pdf_link,
                'document_type': doc_type,
                'year': year,
                'quarter': quarter,
                'period': period,
                'published_date': published_date,
                'metadata': {
                    'source': 'bse_announcements',
                    'category': category,
                    'original_subject': subject,
                    'bse_date': date_str
                }
            }
            
        except Exception as e:
            logger.debug(f"Error parsing announcement row: {e}")
            return None
    
    def _parse_result_row(self, date_str: str, period: str, 
                         pdf_link: str, company: Company) -> Optional[Dict]:
        """Parse individual financial result row"""
        try:
            # Financial results are typically quarterly
            doc_type = 'quarterly_result'
            if 'annual' in period.lower() or 'yearly' in period.lower():
                doc_type = 'annual_report'
            
            # Extract year and quarter information
            year = extract_year_from_text(period + ' ' + date_str)
            quarter = self._extract_quarter(period)
            
            # Parse date
            published_date = None
            if date_str:
                published_date = self._parse_bse_date(date_str)
            
            # Use period as provided
            clean_period = period.strip()
            
            return {
                'title': f"Financial Results - {clean_period}",
                'url': pdf_link,
                'document_type': doc_type,
                'year': year,
                'quarter': quarter,
                'period': clean_period,
                'published_date': published_date,
                'metadata': {
                    'source': 'bse_results',
                    'original_period': period,
                    'bse_date': date_str
                }
            }
            
        except Exception as e:
            logger.debug(f"Error parsing result row: {e}")
            return None
    
    def _parse_bse_date(self, date_str: str) -> Optional[datetime]:
        """Parse BSE date string to datetime"""
        if not date_str:
            return None
        
        # Common BSE date formats
        date_formats = [
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%d %m %Y',
            '%d/%m/%y',
            '%d-%m-%y'
        ]
        
        for date_format in date_formats:
            try:
                return datetime.strptime(date_str.strip(), date_format)
            except ValueError:
                continue
        
        logger.debug(f"Could not parse BSE date: {date_str}")
        return None
    
    def _extract_quarter(self, text: str) -> Optional[str]:
        """Extract quarter information from text"""
        if not text:
            return None
        
        text = text.lower()
        
        # Quarter patterns
        quarter_patterns = {
            'Q1': ['q1', 'first quarter', '1st quarter', 'quarter 1', 'qtr 1'],
            'Q2': ['q2', 'second quarter', '2nd quarter', 'quarter 2', 'qtr 2'],
            'Q3': ['q3', 'third quarter', '3rd quarter', 'quarter 3', 'qtr 3'],
            'Q4': ['q4', 'fourth quarter', '4th quarter', 'quarter 4', 'qtr 4']
        }
        
        for quarter, patterns in quarter_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return quarter
        
        return None
    
    def scrape_company(self, company: Company) -> Dict:
        """Scrape all documents for a specific company"""
        start_time = datetime.now()
        
        try:
            # Get company symbol safely for logging
            try:
                company_symbol = company.symbol
            except Exception as e:
                logger.error(f"Unable to access company symbol: {e}")
                return {
                    'status': 'failed',
                    'message': f'Failed to access company attributes: {str(e)}',
                    'stats': self.get_stats(),
                    'execution_time': 0
                }
            
            logger.info(f"Starting BSE scraping for {company_symbol}")
            
            # Log scraping start
            self.log_scraping_activity(
                company=company,
                action='scrape_start',
                status='started',
                source_url=self.base_url,
                started_at=start_time
            )
            
            # Discover documents
            documents = self.discover_documents(company)
            
            if not documents:
                logger.warning(f"No documents found for {company_symbol} on BSE")
                return {
                    'status': 'success',
                    'message': 'No documents found',
                    'stats': self.get_stats()
                }
            
            # Download documents
            downloaded_docs = []
            for doc_info in documents:
                try:
                    document = self.download_document(doc_info['url'], company, doc_info)
                    if document:
                        downloaded_docs.append(document)
                except Exception as e:
                    logger.error(f"Failed to download document: {doc_info.get('title', 'Unknown')} - {e}")
                    self.stats['documents_failed'] += 1
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Log completion
            self.log_scraping_activity(
                company=company,
                action='scrape_complete',
                status='success',
                source_url=self.base_url,
                started_at=start_time,
                execution_time=execution_time
            )
            
            logger.info(f"BSE scraping completed for {company_symbol}: {self.get_stats()}")
            
            return {
                'status': 'success',
                'message': f'Successfully processed {len(documents)} documents',
                'documents': downloaded_docs,
                'stats': self.get_stats(),
                'execution_time': execution_time
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Get company symbol for error logging
            try:
                company_symbol = company.symbol
            except:
                company_symbol = "Unknown"
            
            # Log error
            self.log_scraping_activity(
                company=company,
                action='scrape_complete',
                status='failed',
                source_url=self.base_url,
                started_at=start_time,
                execution_time=execution_time,
                error_message=str(e)
            )
            
            logger.error(f"BSE scraping failed for {company_symbol}: {e}")
            
            return {
                'status': 'failed',
                'message': f'Scraping failed: {str(e)}',
                'stats': self.get_stats(),
                'execution_time': execution_time
            }