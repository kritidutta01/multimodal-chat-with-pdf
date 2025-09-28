"""
Base scraper class with common functionality
"""
import time
import logging
import hashlib
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from config.settings import settings, get_company_download_path
from src.database.connection import get_db_session
from src.database.models import Company, Document, ScrapingLog
from src.utils.validators import validate_file_size, validate_file_type
from src.utils.helpers import generate_filename, extract_date_from_text

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all scrapers with common functionality"""
    
    def __init__(self, scraper_name: str):
        self.scraper_name = scraper_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Request configuration
        self.request_delay = settings.REQUEST_DELAY
        self.timeout = settings.REQUEST_TIMEOUT
        self.max_retries = settings.MAX_RETRIES
        
        # Statistics
        self.stats = {
            'documents_found': 0,
            'documents_downloaded': 0,
            'documents_failed': 0,
            'errors': []
        }
    
    def make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and error handling"""
        for attempt in range(self.max_retries):
            try:
                # Add delay between requests
                if attempt > 0:
                    time.sleep(self.request_delay * (2 ** attempt))  # Exponential backoff
                else:
                    time.sleep(self.request_delay)
                
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Check if request was successful
                response.raise_for_status()
                
                logger.debug(f"Successfully fetched: {url}")
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {url} - {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All retry attempts failed for: {url}")
                    self.stats['errors'].append(f"Request failed: {url} - {str(e)}")
                    
        return None
    
    def parse_html(self, response: requests.Response) -> Optional[BeautifulSoup]:
        """Parse HTML response using BeautifulSoup"""
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
            return None
    
    def download_document(self, url: str, company: Company, doc_info: Dict) -> Optional[Document]:
        """Download a document and save metadata to database"""
        try:
            # Make request to download file
            response = self.make_request(url)
            if not response:
                return None
            
            # Validate file
            if not validate_file_size(len(response.content)):
                logger.warning(f"File size validation failed: {url}")
                return None
            
            # Generate filename and path
            filename = generate_filename(
                company.symbol,
                doc_info.get('document_type', 'unknown'),
                doc_info.get('period', ''),
                url
            )
            
            # Get download path
            download_path = get_company_download_path(
                company.symbol,
                doc_info.get('year', datetime.now().year),
                doc_info.get('document_type', 'other')
            )
            download_path.mkdir(parents=True, exist_ok=True)
            
            file_path = download_path / filename
            
            # Calculate file hash for deduplication
            file_hash = hashlib.sha256(response.content).hexdigest()
            
            # Check if document already exists
            with get_db_session() as session:
                existing_doc = session.query(Document).filter(
                    Document.file_hash == file_hash,
                    Document.company_id == company.id
                ).first()
                
                if existing_doc:
                    logger.info(f"Document already exists: {filename}")
                    return existing_doc
            
            # Save file to disk
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Create document record
            document = Document(
                company_id=company.id,
                title=doc_info.get('title', filename),
                document_type=doc_info.get('document_type', 'unknown'),
                period=doc_info.get('period'),
                year=doc_info.get('year'),
                quarter=doc_info.get('quarter'),
                filename=filename,
                file_path=str(file_path),
                file_size=len(response.content),
                file_hash=file_hash,
                file_extension=Path(filename).suffix.lower(),
                source_url=url,
                source_platform=self.scraper_name,
                download_status='completed',
                published_date=doc_info.get('published_date'),
                downloaded_at=datetime.now(),
                metadata=doc_info.get('metadata', {})
            )
            
            # Save to database
            with get_db_session() as session:
                session.add(document)
                session.flush()  # To get the ID
                logger.info(f"Downloaded and saved: {filename} (ID: {document.id})")
            
            self.stats['documents_downloaded'] += 1
            return document
            
        except Exception as e:
            logger.error(f"Failed to download document {url}: {e}")
            self.stats['documents_failed'] += 1
            self.stats['errors'].append(f"Download failed: {url} - {str(e)}")
            return None
    
    def log_scraping_activity(self, company: Optional[Company], action: str, 
                            status: str, **kwargs):
        """Log scraping activity to database"""
        try:
            # Get company_id safely
            company_id = None
            if company:
                try:
                    company_id = company.id
                except:
                    # If company object is detached, we might not be able to access id
                    # In this case, we'll log without company_id
                    logger.warning("Unable to access company.id - company object may be detached")
            
            log_entry = ScrapingLog(
                company_id=company_id,
                scraper_name=self.scraper_name,
                source_url=kwargs.get('source_url', ''),
                action=action,
                status=status,
                documents_found=self.stats['documents_found'],
                documents_downloaded=self.stats['documents_downloaded'],
                documents_failed=self.stats['documents_failed'],
                error_message=kwargs.get('error_message'),
                error_code=kwargs.get('error_code'),
                execution_time=kwargs.get('execution_time'),
                response_time=kwargs.get('response_time'),
                started_at=kwargs.get('started_at'),
                completed_at=datetime.now(),
                metadata={
                    'stats': self.stats.copy(),
                    'additional_info': kwargs.get('metadata', {})
                }
            )
            
            with get_db_session() as session:
                session.add(log_entry)
            
            logger.debug(f"Logged scraping activity: {action} - {status}")
            
        except Exception as e:
            logger.error(f"Failed to log scraping activity: {e}")
    
    def reset_stats(self):
        """Reset scraping statistics"""
        self.stats = {
            'documents_found': 0,
            'documents_downloaded': 0,
            'documents_failed': 0,
            'errors': []
        }
    
    def get_stats(self) -> Dict:
        """Get current scraping statistics"""
        return self.stats.copy()
    
    @abstractmethod
    def discover_documents(self, company: Company) -> List[Dict]:
        """Discover available documents for a company"""
        pass
    
    @abstractmethod
    def scrape_company(self, company: Company) -> Dict:
        """Scrape all documents for a specific company"""
        pass
    
    def scrape_companies(self, companies: List[Company]) -> Dict:
        """Scrape documents for multiple companies"""
        overall_stats = {
            'total_companies': len(companies),
            'successful_companies': 0,
            'failed_companies': 0,
            'total_documents_found': 0,
            'total_documents_downloaded': 0,
            'total_documents_failed': 0,
            'errors': []
        }
        
        for company in companies:
            try:
                logger.info(f"Starting scraping for company: {company.symbol}")
                self.reset_stats()
                
                result = self.scrape_company(company)
                
                if result.get('status') == 'success':
                    overall_stats['successful_companies'] += 1
                else:
                    overall_stats['failed_companies'] += 1
                
                # Aggregate statistics
                stats = self.get_stats()
                overall_stats['total_documents_found'] += stats['documents_found']
                overall_stats['total_documents_downloaded'] += stats['documents_downloaded']
                overall_stats['total_documents_failed'] += stats['documents_failed']
                overall_stats['errors'].extend(stats['errors'])
                
                logger.info(f"Completed scraping for {company.symbol}: {stats}")
                
            except Exception as e:
                logger.error(f"Failed to scrape company {company.symbol}: {e}")
                overall_stats['failed_companies'] += 1
                overall_stats['errors'].append(f"Company {company.symbol}: {str(e)}")
        
        logger.info(f"Scraping completed. Overall stats: {overall_stats}")
        return overall_stats
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'session'):
            self.session.close()