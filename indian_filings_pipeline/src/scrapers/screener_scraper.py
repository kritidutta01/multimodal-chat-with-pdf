"""
Screener.in scraper for company financial data and documents
"""
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote

from .base_scraper import BaseScraper
from src.database.models import Company
from src.utils.helpers import extract_year_from_text, classify_document_type, normalize_company_name
from config.settings import settings

logger = logging.getLogger(__name__)

class ScreenerScraper(BaseScraper):
    """Scraper for Screener.in website"""
    
    def __init__(self):
        super().__init__("screener_scraper")
        self.base_url = "https://www.screener.in"
        
        # Screener.in specific URL patterns
        self.search_url = f"{self.base_url}/api/company/search/"
        self.company_url = f"{self.base_url}/company"
        
        # Document type patterns for Screener.in
        self.doc_patterns = {
            'annual_report': ['annual report', 'annual', 'yearly report', 'ar'],
            'quarterly_result': ['quarterly', 'quarter', 'q1', 'q2', 'q3', 'q4', 'result', 'financial result'],
            'presentation': ['presentation', 'investor', 'ppt', 'slides', 'earnings call', 'concall'],
            'board_meeting': ['board meeting', 'board', 'meeting outcome', 'intimation'],
            'shareholding': ['shareholding pattern', 'shareholding', 'shares holding'],
            'financial_statement': ['balance sheet', 'profit loss', 'cash flow', 'financial statement'],
            'other': ['notice', 'announcement', 'disclosure', 'intimation', 'outcome']
        }
        
        # Headers specific to screener.in to avoid blocking
        self.session.headers.update({
            'Referer': 'https://www.screener.in/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
    
    def discover_documents(self, company: Company) -> List[Dict]:
        """Discover available documents for a company from Screener.in"""
        documents = []
        
        try:
            # Get company symbol safely for logging
            try:
                company_symbol = company.symbol
            except Exception as e:
                logger.error(f"Unable to access company symbol: {e}")
                return documents
            
            # First, find the company on screener.in
            company_url = self._find_company_url(company)
            if not company_url:
                logger.warning(f"Company {company_symbol} not found on Screener.in")
                return documents
            
            # Get documents from company page
            company_docs = self._get_company_documents(company_url, company)
            documents.extend(company_docs)
            
            # Get documents from annual reports section
            annual_docs = self._get_annual_reports(company_url, company)
            documents.extend(annual_docs)
            
            # Get documents from quarterly results section
            quarterly_docs = self._get_quarterly_results(company_url, company)
            documents.extend(quarterly_docs)
            
            self.stats['documents_found'] = len(documents)
            logger.info(f"Found {len(documents)} documents for {company_symbol} on Screener.in")
            
        except Exception as e:
            logger.error(f"Error discovering documents: {e}")
            self.stats['errors'].append(f"Discovery error: {str(e)}")
        
        return documents
    
    def _find_company_url(self, company: Company) -> Optional[str]:
        """Find the company URL on screener.in"""
        try:
            # Get company attributes safely
            try:
                company_symbol = company.symbol
                company_name = company.name
            except Exception as e:
                logger.error(f"Unable to access company attributes: {e}")
                return None
            
            # Try different search terms
            search_terms = [
                company_symbol,
                company_name,
                normalize_company_name(company_name)
            ]
            
            for search_term in search_terms:
                # Search using screener.in search API
                search_url = f"{self.search_url}?q={quote(search_term)}"
                response = self.make_request(search_url)
                
                if response:
                    try:
                        search_results = response.json()
                        
                        # Look for exact or close matches
                        for result in search_results:
                            result_name = result.get('name', '').lower()
                            result_symbol = result.get('symbol', '').lower()
                            
                            # Check for symbol match
                            if company_symbol.lower() == result_symbol:
                                company_id = result.get('id')
                                return f"{self.company_url}/{company_id}/"
                            
                            # Check for name match
                            normalized_result = normalize_company_name(result_name)
                            normalized_search = normalize_company_name(company_name)
                            
                            if normalized_result == normalized_search:
                                company_id = result.get('id')
                                return f"{self.company_url}/{company_id}/"
                    
                    except Exception as e:
                        logger.debug(f"Error parsing search results: {e}")
                        continue
            
            # If API search fails, try direct URL construction
            # Many companies follow the pattern: /company/{symbol}/
            direct_url = f"{self.company_url}/{company_symbol.lower()}/"
            response = self.make_request(direct_url)
            if response and response.status_code == 200:
                return direct_url
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding company URL: {e}")
            return None
    
    def _get_company_documents(self, company_url: str, company: Company) -> List[Dict]:
        """Get documents from main company page"""
        documents = []
        
        try:
            response = self.make_request(company_url)
            if not response:
                return documents
            
            soup = self.parse_html(response)
            if not soup:
                return documents
            
            # Look for document links in various sections
            # Screener.in usually has documents in "Documents" or "Reports" sections
            document_sections = soup.find_all(['div', 'section'], 
                                            text=re.compile(r'documents|reports|annual|quarterly', re.I))
            
            for section in document_sections:
                # Find parent container and look for links
                container = section.find_parent(['div', 'section', 'article'])
                if container:
                    links = container.find_all('a', href=True)
                    for link in links:
                        href = link.get('href')
                        text = link.get_text(strip=True)
                        
                        if self._is_document_link(href, text):
                            doc_info = self._parse_document_link(href, text, company_url, company)
                            if doc_info:
                                documents.append(doc_info)
            
            # Also look for direct PDF/Excel links anywhere on the page
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href')
                text = link.get_text(strip=True)
                
                if self._is_document_link(href, text):
                    doc_info = self._parse_document_link(href, text, company_url, company)
                    if doc_info:
                        documents.append(doc_info)
            
        except Exception as e:
            logger.error(f"Error getting company documents: {e}")
        
        return documents
    
    def _get_annual_reports(self, company_url: str, company: Company) -> List[Dict]:
        """Get annual reports from company page"""
        documents = []
        import pdb;pdb.set_trace()
        try:
            # Try to access annual reports section
            annual_url = f"{company_url}annual-reports/"
            response = self.make_request(annual_url)
            
            if response and response.status_code == 200:
                soup = self.parse_html(response)
                if soup:
                    # Parse annual reports table/list
                    documents.extend(self._parse_reports_page(soup, company_url, company, 'annual_report'))
            
        except Exception as e:
            logger.debug(f"Error getting annual reports: {e}")
        
        return documents
    
    def _get_quarterly_results(self, company_url: str, company: Company) -> List[Dict]:
        """Get quarterly results from company page"""
        documents = []
        
        try:
            # Try to access quarterly results section
            quarterly_url = f"{company_url}quarterly-results/"
            response = self.make_request(quarterly_url)
            
            if response and response.status_code == 200:
                soup = self.parse_html(response)
                if soup:
                    # Parse quarterly results table/list
                    documents.extend(self._parse_reports_page(soup, company_url, company, 'quarterly_result'))
            
        except Exception as e:
            logger.debug(f"Error getting quarterly results: {e}")
        
        return documents
    
    def _parse_reports_page(self, soup, company_url: str, company: Company, default_doc_type: str) -> List[Dict]:
        """Parse a reports page (annual reports or quarterly results)"""
        documents = []
        
        try:
            # Look for tables with reports
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        # Usually: Date | Report Type | Link
                        date_cell = cells[0].get_text(strip=True)
                        
                        # Find link in any cell
                        link = None
                        link_text = ""
                        for cell in cells:
                            link_elem = cell.find('a', href=True)
                            if link_elem:
                                link = link_elem.get('href')
                                link_text = link_elem.get_text(strip=True)
                                break
                        
                        if link and self._is_document_link(link, link_text):
                            doc_info = self._parse_document_link(
                                link, f"{date_cell} {link_text}", company_url, company, default_doc_type
                            )
                            if doc_info:
                                documents.append(doc_info)
            
            # Also look for list items with reports
            lists = soup.find_all(['ul', 'ol'])
            for list_elem in lists:
                items = list_elem.find_all('li')
                for item in items:
                    link = item.find('a', href=True)
                    if link:
                        href = link.get('href')
                        text = item.get_text(strip=True)
                        
                        if self._is_document_link(href, text):
                            doc_info = self._parse_document_link(href, text, company_url, company, default_doc_type)
                            if doc_info:
                                documents.append(doc_info)
        
        except Exception as e:
            logger.error(f"Error parsing reports page: {e}")
        
        return documents
    
    def _is_document_link(self, href: str, text: str) -> bool:
        """Check if a link points to a document"""
        if not href:
            return False
        
        # Check file extensions
        document_extensions = ['.pdf', '.xls', '.xlsx', '.doc', '.docx', '.ppt', '.pptx']
        if any(href.lower().endswith(ext) for ext in document_extensions):
            return True
        
        # Check for document-related text
        document_keywords = ['annual report', 'quarterly', 'result', 'presentation', 'financial', 'statement']
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in document_keywords):
            return True
        
        # Check for links that might lead to documents
        if 'download' in href.lower() or 'document' in href.lower() or 'report' in href.lower():
            return True
        
        return False
    
    def _parse_document_link(self, href: str, text: str, company_url: str, 
                            company: Company, default_doc_type: str = None) -> Optional[Dict]:
        """Parse a document link and extract information"""
        try:
            # Make URL absolute
            if href.startswith('/'):
                url = urljoin(self.base_url, href)
            elif href.startswith('http'):
                url = href
            else:
                url = urljoin(company_url, href)
            
            # Classify document type
            combined_text = f"{text} {href}".lower()
            doc_type = classify_document_type(combined_text, self.doc_patterns)
            
            # Use default type if classification fails
            if doc_type == 'other' and default_doc_type:
                doc_type = default_doc_type
            
            # Extract year and period information
            year = extract_year_from_text(combined_text)
            quarter = self._extract_quarter(combined_text)
            
            # Generate period string
            period = None
            if quarter and year:
                period = f"{quarter}FY{year}"
            elif year:
                period = f"FY{year}"
            
            # Clean up title
            title = text.strip()
            if not title:
                title = f"Screener.in Document - {doc_type}"
            
            return {
                'title': title,
                'url': url,
                'document_type': doc_type,
                'year': year,
                'quarter': quarter,
                'period': period,
                'published_date': None,  # Screener.in doesn't always provide clear dates
                'metadata': {
                    'source': 'screener.in',
                    'original_text': text,
                    'original_href': href,
                    'company_url': company_url
                }
            }
            
        except Exception as e:
            logger.debug(f"Error parsing document link: {e}")
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
            
            logger.info(f"Starting Screener.in scraping for {company_symbol}")
            
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
                logger.warning(f"No documents found for {company_symbol} on Screener.in")
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
            
            logger.info(f"Screener.in scraping completed for {company_symbol}: {self.get_stats()}")
            
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
            
            logger.error(f"Screener.in scraping failed for {company_symbol}: {e}")
            
            return {
                'status': 'failed',
                'message': f'Scraping failed: {str(e)}',
                'stats': self.get_stats(),
                'execution_time': execution_time
            }