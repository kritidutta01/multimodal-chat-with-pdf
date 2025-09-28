"""
NSE (National Stock Exchange) scraper for company filings
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

class NSEScraper(BaseScraper):
    """Scraper for NSE India website"""
    
    def __init__(self):
        super().__init__("nse_scraper")
        self.base_url = settings.NSE_BASE_URL
        
        # NSE specific URL patterns
        self.company_info_url = f"{self.base_url}/api/quote-equity"
        self.corporate_actions_url = f"{self.base_url}/api/corporates-corporateActions"
        self.financial_results_url = f"{self.base_url}/api/corporates-financial-results"
        
        # Document type patterns for NSE
        self.doc_patterns = {
            'annual_report': ['annual report', 'annual', 'yearly report'],
            'quarterly_result': ['quarterly', 'quarter', 'q1', 'q2', 'q3', 'q4', 'result'],
            'presentation': ['presentation', 'investor', 'ppt', 'slides', 'earnings call'],
            'board_meeting': ['board meeting', 'board', 'meeting outcome'],
            'shareholding': ['shareholding pattern', 'shareholding', 'shares'],
            'other': ['notice', 'announcement', 'disclosure']
        }
    
    def discover_documents(self, company: Company) -> List[Dict]:
        """Discover available documents for a company from NSE"""
        documents = []
        
        try:
            # Get company symbol safely for logging
            try:
                company_symbol = company.symbol
            except Exception as e:
                logger.error(f"Unable to access company symbol: {e}")
                return documents
            
            # Get corporate actions and announcements
            corporate_docs = self._get_corporate_actions(company)
            documents.extend(corporate_docs)
            
            # Get financial results
            financial_docs = self._get_financial_results(company)
            documents.extend(financial_docs)
            
            self.stats['documents_found'] = len(documents)
            logger.info(f"Found {len(documents)} documents for {company_symbol} on NSE")
            
        except Exception as e:
            logger.error(f"Error discovering documents: {e}")
            self.stats['errors'].append(f"Discovery error: {str(e)}")
        
        return documents
    
    def _get_corporate_actions(self, company: Company) -> List[Dict]:
        """Get corporate actions and related documents"""
        documents = []
        
        try:
            # Get company symbol safely
            try:
                nse_symbol = company.nse_symbol or company.symbol
                company_symbol = company.symbol
            except Exception as e:
                logger.error(f"Unable to access company attributes: {e}")
                return documents
            
            # NSE corporate actions API
            params = {
                'symbol': nse_symbol,
                'index': 'equities'
            }
            
            response = self.make_request(self.corporate_actions_url, params=params)
            if not response:
                return documents
            
            data = response.json()
            
            # Parse corporate actions data
            if 'data' in data:
                for item in data['data']:
                    # Extract document information
                    doc_info = self._parse_corporate_action(item, company)
                    if doc_info:
                        documents.append(doc_info)
            
        except Exception as e:
            logger.error(f"Error fetching corporate actions for {company_symbol}: {e}")
        
        return documents
    
    def _get_financial_results(self, company: Company) -> List[Dict]:
        """Get financial results and related documents"""
        documents = []
        
        try:
            # Get company symbol safely
            try:
                nse_symbol = company.nse_symbol or company.symbol
                company_symbol = company.symbol
            except Exception as e:
                logger.error(f"Unable to access company attributes: {e}")
                return documents
            
            # NSE financial results API
            params = {
                'symbol': nse_symbol,
                'index': 'equities'
            }
            
            response = self.make_request(self.financial_results_url, params=params)
            if not response:
                return documents
            
            data = response.json()
            
            # Parse financial results data
            if 'data' in data:
                for item in data['data']:
                    # Extract document information
                    doc_info = self._parse_financial_result(item, company)
                    if doc_info:
                        documents.append(doc_info)
            
        except Exception as e:
            logger.error(f"Error fetching financial results for {company_symbol}: {e}")
        
        return documents
    
    def _parse_corporate_action(self, item: Dict, company: Company) -> Optional[Dict]:
        """Parse corporate action item and extract document info"""
        try:
            # Extract relevant information
            subject = item.get('subject', '').lower()
            desc = item.get('desc', '').lower()
            attachment_url = item.get('attchmntFile', '')
            date_str = item.get('an_dt', '')
            
            # Skip if no attachment
            if not attachment_url:
                return None
            
            # Classify document type
            doc_type = classify_document_type(subject + ' ' + desc, self.doc_patterns)
            
            # Extract year and period
            year = extract_year_from_text(subject + ' ' + desc + ' ' + date_str)
            quarter = self._extract_quarter(subject + ' ' + desc)
            
            # Parse date
            published_date = None
            if date_str:
                try:
                    published_date = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    try:
                        published_date = datetime.strptime(date_str, '%d-%m-%Y')
                    except:
                        pass
            
            return {
                'title': item.get('subject', 'NSE Document'),
                'url': attachment_url,
                'document_type': doc_type,
                'year': year,
                'quarter': quarter,
                'period': f"FY{year}" if year else None,
                'published_date': published_date,
                'metadata': {
                    'source': 'nse_corporate_actions',
                    'description': item.get('desc', ''),
                    'original_data': item
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing corporate action: {e}")
            return None
    
    def _parse_financial_result(self, item: Dict, company: Company) -> Optional[Dict]:
        """Parse financial result item and extract document info"""
        try:
            # Extract relevant information
            period = item.get('period', '').lower()
            desc = item.get('desc', '').lower()
            attachment_url = item.get('attchmntFile', '')
            date_str = item.get('re_date', '')
            
            # Skip if no attachment
            if not attachment_url:
                return None
            
            # Classify document type (financial results are usually quarterly)
            doc_type = 'quarterly_result'
            if 'annual' in period or 'yearly' in period:
                doc_type = 'annual_report'
            
            # Extract year and quarter
            year = extract_year_from_text(period + ' ' + desc + ' ' + date_str)
            quarter = self._extract_quarter(period + ' ' + desc)
            
            # Parse date
            published_date = None
            if date_str:
                try:
                    published_date = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    try:
                        published_date = datetime.strptime(date_str, '%d-%m-%Y')
                    except:
                        pass
            
            return {
                'title': f"Financial Results - {period}",
                'url': attachment_url,
                'document_type': doc_type,
                'year': year,
                'quarter': quarter,
                'period': period,
                'published_date': published_date,
                'metadata': {
                    'source': 'nse_financial_results',
                    'description': item.get('desc', ''),
                    'original_data': item
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing financial result: {e}")
            return None
    
    def _extract_quarter(self, text: str) -> Optional[str]:
        """Extract quarter information from text"""
        text = text.lower()
        
        # Quarter patterns
        quarter_patterns = {
            'q1': ['q1', 'first quarter', '1st quarter', 'quarter 1'],
            'q2': ['q2', 'second quarter', '2nd quarter', 'quarter 2'],
            'q3': ['q3', 'third quarter', '3rd quarter', 'quarter 3'],
            'q4': ['q4', 'fourth quarter', '4th quarter', 'quarter 4']
        }
        
        for quarter, patterns in quarter_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return quarter.upper()
        
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
            
            logger.info(f"Starting NSE scraping for {company_symbol}")
            
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
                logger.warning(f"No documents found for {company_symbol} on NSE")
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
            
            logger.info(f"NSE scraping completed for {company_symbol}: {self.get_stats()}")
            
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
            
            logger.error(f"NSE scraping failed for {company_symbol}: {e}")
            
            return {
                'status': 'failed',
                'message': f'Scraping failed: {str(e)}',
                'stats': self.get_stats(),
                'execution_time': execution_time
            }