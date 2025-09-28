"""
Utility functions for scrapers
"""
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def get_available_scrapers() -> Dict[str, str]:
    """Get list of available scrapers"""
    return {
        'nse': 'NSE (National Stock Exchange) scraper',
        'bse': 'BSE (Bombay Stock Exchange) scraper', 
        'screener': 'Screener.in financial data scraper'
    }

def validate_scraper_name(scraper_name: str) -> bool:
    """Validate if scraper name is available"""
    available_scrapers = get_available_scrapers()
    return scraper_name in available_scrapers

def get_scraper_class(scraper_name: str):
    """Get scraper class by name"""
    from .nse_scraper import NSEScraper
    from .bse_scraper import BSEScraper
    from .screener_scraper import ScreenerScraper
    
    scraper_classes = {
        'nse': NSEScraper,
        'bse': BSEScraper,
        'screener': ScreenerScraper
    }
    
    return scraper_classes.get(scraper_name)

def clean_document_title(title: str) -> str:
    """Clean and standardize document titles"""
    if not title:
        return "Unknown Document"
    
    # Remove extra whitespace
    title = re.sub(r'\s+', ' ', title.strip())
    
    # Remove common prefixes that don't add value
    prefixes_to_remove = [
        'download', 'view', 'pdf', 'excel', 'document'
    ]
    
    title_lower = title.lower()
    for prefix in prefixes_to_remove:
        if title_lower.startswith(prefix):
            title = title[len(prefix):].strip()
            break
    
    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]
    
    return title

def extract_file_extension_from_url(url: str) -> str:
    """Extract file extension from URL"""
    # Remove query parameters and fragments
    clean_url = url.split('?')[0].split('#')[0]
    
    # Get extension
    if '.' in clean_url:
        extension = clean_url.split('.')[-1].lower()
        # Validate it's a real extension
        if len(extension) <= 5 and extension.isalnum():
            return f".{extension}"
    
    return ""

def is_financial_document(title: str, url: str) -> bool:
    """Check if document appears to be financial/company related"""
    text = f"{title} {url}".lower()
    
    financial_keywords = [
        'annual', 'quarterly', 'financial', 'result', 'report', 'statement',
        'balance sheet', 'profit', 'loss', 'cash flow', 'earnings',
        'presentation', 'investor', 'shareholding', 'board meeting'
    ]
    
    return any(keyword in text for keyword in financial_keywords)

def normalize_financial_period(period_text: str) -> Optional[str]:
    """Normalize financial period text to standard format"""
    if not period_text:
        return None
    
    text = period_text.lower().strip()
    
    # FY patterns
    fy_patterns = [
        (r'fy\s*(\d{4})', r'FY\1'),
        (r'fy\s*(\d{2})', r'FY20\1'),
        (r'(\d{4})-(\d{2})', r'FY\1'),
        (r'financial year\s*(\d{4})', r'FY\1')
    ]
    
    for pattern, replacement in fy_patterns:
        match = re.search(pattern, text)
        if match:
            return re.sub(pattern, replacement, text)
    
    # Quarter patterns
    quarter_patterns = [
        (r'q([1-4])\s*fy\s*(\d{4})', r'Q\1FY\2'),
        (r'quarter\s*([1-4])\s*(\d{4})', r'Q\1FY\2'),
        (r'([1-4])(?:st|nd|rd|th)\s*quarter\s*(\d{4})', r'Q\1FY\2')
    ]
    
    for pattern, replacement in quarter_patterns.items():
        match = re.search(pattern, text)
        if match:
            return re.sub(pattern, replacement, text)
    
    return period_text

def get_document_priority(doc_type: str) -> int:
    """Get priority for document types (lower number = higher priority)"""
    priority_map = {
        'annual_report': 1,
        'quarterly_result': 2,
        'financial_statement': 3,
        'presentation': 4,
        'board_meeting': 5,
        'shareholding': 6,
        'other': 10
    }
    
    return priority_map.get(doc_type, 10)

def deduplicate_documents(documents: List[Dict]) -> List[Dict]:
    """Remove duplicate documents based on URL and title similarity"""
    if not documents:
        return []
    
    unique_docs = []
    seen_urls = set()
    seen_titles = set()
    
    # Sort by priority first
    sorted_docs = sorted(documents, key=lambda x: get_document_priority(x.get('document_type', 'other')))
    
    for doc in sorted_docs:
        url = doc.get('url', '')
        title = doc.get('title', '').lower().strip()
        
        # Skip if exact URL already seen
        if url in seen_urls:
            continue
        
        # Skip if very similar title already seen
        title_similar = False
        for seen_title in seen_titles:
            if title and seen_title:
                # Simple similarity check
                common_words = set(title.split()) & set(seen_title.split())
                if len(common_words) >= min(len(title.split()), len(seen_title.split())) * 0.8:
                    title_similar = True
                    break
        
        if not title_similar:
            unique_docs.append(doc)
            seen_urls.add(url)
            seen_titles.add(title)
    
    logger.info(f"Deduplicated documents: {len(documents)} -> {len(unique_docs)}")
    return unique_docs

def calculate_scraper_success_rate(stats: Dict) -> float:
    """Calculate success rate for scraper statistics"""
    total_found = stats.get('documents_found', 0)
    total_downloaded = stats.get('documents_downloaded', 0)
    
    if total_found == 0:
        return 0.0
    
    return (total_downloaded / total_found) * 100

def format_scraper_stats(stats: Dict) -> str:
    """Format scraper statistics for display"""
    success_rate = calculate_scraper_success_rate(stats)
    
    return (f"Found: {stats.get('documents_found', 0)}, "
            f"Downloaded: {stats.get('documents_downloaded', 0)}, "
            f"Failed: {stats.get('documents_failed', 0)}, "
            f"Success Rate: {success_rate:.1f}%")

def get_scraper_health_status(stats: Dict) -> str:
    """Get health status based on scraper stats"""
    success_rate = calculate_scraper_success_rate(stats)
    error_count = len(stats.get('errors', []))
    
    if success_rate >= 80 and error_count <= 2:
        return "healthy"
    elif success_rate >= 50 and error_count <= 5:
        return "degraded"
    else:
        return "unhealthy"