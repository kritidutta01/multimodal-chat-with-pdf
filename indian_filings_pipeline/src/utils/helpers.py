"""
Utility helper functions
"""
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urlparse
from slugify import slugify

def generate_filename(company_symbol: str, doc_type: str, period: str, url: str, year: Optional[int] = None) -> str:
    """Generate a standardized filename for documents

    Args:
        company_symbol: Company stock symbol
        doc_type: Type of document (annual_report, quarterly_result, etc.)
        period: Period string (e.g., FY2024, Q1FY2024)
        url: Source URL to extract file extension
        year: Optional year of the document

    Returns:
        Standardized filename in format: SYMBOL_doctype_FY2024.pdf
    """

    # Clean inputs
    company_symbol = company_symbol.upper()
    doc_type = slugify(doc_type).replace('-', '_')

    # Extract file extension from URL
    parsed_url = urlparse(url)
    path = Path(parsed_url.path)
    extension = path.suffix.lower()

    # Default to .pdf if no extension found
    if not extension or extension not in ['.pdf', '.xls', '.xlsx', '.doc', '.docx', '.ppt', '.pptx']:
        extension = '.pdf'

    # Build period/year component
    year_component = ""
    if period:
        # Clean up period string
        period_clean = slugify(period).replace('-', '_').upper()
        # Remove redundant prefixes
        period_clean = re.sub(r'^(FY|Q\d)', lambda m: m.group(0), period_clean, flags=re.IGNORECASE)
        year_component = period_clean
    elif year:
        year_component = f"FY{year}"

    # Construct filename based on available information
    if year_component:
        filename = f"{company_symbol}_{doc_type}_{year_component}{extension}"
    else:
        # If no year info, add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{company_symbol}_{doc_type}_{timestamp}{extension}"

    # Ensure filename is not too long (max 255 chars for most filesystems)
    max_length = 200
    if len(filename) > max_length:
        # Calculate available space
        fixed_parts_len = len(company_symbol) + len(extension) + 2  # 2 for underscores
        available_len = max_length - fixed_parts_len

        # Truncate doc_type and year_component proportionally
        max_doc_type_len = min(len(doc_type), available_len // 2)
        max_year_len = min(len(year_component), available_len - max_doc_type_len - 1)

        doc_type = doc_type[:max_doc_type_len]
        year_component = year_component[:max_year_len] if year_component else ""

        if year_component:
            filename = f"{company_symbol}_{doc_type}_{year_component}{extension}"
        else:
            filename = f"{company_symbol}_{doc_type}{extension}"

    return filename

def extract_year_from_text(text: str) -> Optional[int]:
    """Extract year from text content (document titles, URLs, etc.)"""
    if not text:
        return None

    # Common year patterns - ordered by specificity
    year_patterns = [
        # FY patterns
        r'FY[_\s-]*(\d{4})[_\s-]*\d{2}',  # FY2023-24, FY2023_24, FY 2023-24
        r'FY[_\s-]*(\d{4})',  # FY2024, FY_2024, FY 2024
        r'FY[_\s-]*(\d{2})[_\s-]*\d{2}',  # FY23-24, FY_23_24
        r'FY[_\s-]*(\d{2})',  # FY24, FY_24, FY 24

        # Year ranges
        r'(\d{4})[_\s-]+\d{2,4}',  # 2023-24, 2023_24, 2023-2024

        # Annual report patterns
        r'annual[_\s-]+report[_\s-]+(\d{4})',  # annual-report-2024
        r'(\d{4})[_\s-]+annual',  # 2024-annual
        r'AR[_\s-]*(\d{4})',  # AR2024, AR_2024

        # Generic 4-digit years
        r'\b(20\d{2})\b',  # 2020, 2021, etc. (must be word boundary)

        # 2-digit years (less specific, check last)
        r'[_\s-](\d{2})[_\s-]',  # _23_, -24-
    ]

    current_year = datetime.now().year

    for pattern in year_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                year_str = str(match).strip()

                # Convert to 4-digit year
                if len(year_str) == 2:
                    year = 2000 + int(year_str)
                else:
                    year = int(year_str)

                # Validate year range (2000 to current year + 1)
                if 2000 <= year <= current_year + 1:
                    return year

            except (ValueError, AttributeError):
                continue

    return None

def extract_date_from_text(text: str) -> Optional[datetime]:
    """Extract date from text content"""
    if not text:
        return None
    
    # Common date patterns
    date_patterns = [
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',  # DD/MM/YYYY or DD-MM-YYYY
        r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
        r'\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b',  # DD Month YYYY
        r'\b([A-Za-z]+\s+\d{1,2},?\s+\d{4})\b',  # Month DD, YYYY
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                # Try different date formats
                for date_format in ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%d',
                                   '%d %B %Y', '%d %b %Y', '%B %d, %Y', '%b %d, %Y']:
                    try:
                        return datetime.strptime(match, date_format)
                    except ValueError:
                        continue
            except:
                continue
    
    return None

def classify_document_type(text: str, doc_patterns: Dict[str, List[str]]) -> str:
    """Classify document type based on text content"""
    if not text:
        return 'other'
    
    text = text.lower()
    
    # Score each document type
    scores = {}
    for doc_type, patterns in doc_patterns.items():
        score = 0
        for pattern in patterns:
            if pattern.lower() in text:
                score += 1
        scores[doc_type] = score
    
    # Return the type with highest score
    if scores:
        best_type = max(scores, key=scores.get)
        if scores[best_type] > 0:
            return best_type
    
    return 'other'

def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()

def normalize_company_name(name: str) -> str:
    """Normalize company name for comparison"""
    if not name:
        return ""
    
    # Convert to lowercase and remove common suffixes
    normalized = name.lower()
    suffixes_to_remove = [
        ' limited', ' ltd', ' ltd.', ' private limited', ' pvt ltd', ' pvt. ltd.',
        ' corporation', ' corp', ' corp.', ' company', ' co', ' co.',
        ' incorporated', ' inc', ' inc.'
    ]
    
    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            break
    
    # Remove extra whitespace and special characters
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def extract_quarter_from_text(text: str) -> Optional[str]:
    """Extract quarter information from text"""
    if not text:
        return None
    
    text = text.lower()
    
    # Quarter patterns with common variations
    quarter_patterns = {
        'Q1': ['q1', 'first quarter', '1st quarter', 'quarter 1', 'quarter i', 'qtr 1'],
        'Q2': ['q2', 'second quarter', '2nd quarter', 'quarter 2', 'quarter ii', 'qtr 2'],
        'Q3': ['q3', 'third quarter', '3rd quarter', 'quarter 3', 'quarter iii', 'qtr 3'],
        'Q4': ['q4', 'fourth quarter', '4th quarter', 'quarter 4', 'quarter iv', 'qtr 4']
    }
    
    for quarter, patterns in quarter_patterns.items():
        for pattern in patterns:
            if pattern in text:
                return quarter
    
    return None

def extract_financial_year(text: str) -> Optional[str]:
    """Extract financial year from text"""
    if not text:
        return None
    
    # FY patterns
    fy_patterns = [
        r'\bFY\s*(\d{4})\b',  # FY2024
        r'\bFY\s*(\d{2})\b',  # FY24
        r'\bFY\s*(\d{4})-(\d{2})\b',  # FY2023-24
        r'\bFY\s*(\d{2})-(\d{2})\b',  # FY23-24
        r'\b(\d{4})-(\d{2})\s*FY\b',  # 2023-24 FY
    ]
    
    for pattern in fy_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                if isinstance(match, tuple):
                    # Handle FY ranges like 2023-24
                    year = int(match[0]) if len(match[0]) == 4 else 2000 + int(match[0])
                else:
                    # Handle single year
                    year = int(match) if len(match) == 4 else 2000 + int(match)
                
                # Validate year
                if 2000 <= year <= datetime.now().year + 1:
                    return f"FY{year}"
                    
            except ValueError:
                continue
    
    return None

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_file_extension_from_url(url: str) -> str:
    """Get file extension from URL"""
    try:
        parsed_url = urlparse(url)
        path = Path(parsed_url.path)
        return path.suffix.lower()
    except:
        return ""

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def parse_period_string(period: str) -> Dict[str, Optional[str]]:
    """Parse period string to extract year, quarter, and financial year"""
    result = {
        'year': None,
        'quarter': None,
        'financial_year': None
    }
    
    if not period:
        return result
    
    # Extract components
    result['year'] = extract_year_from_text(period)
    result['quarter'] = extract_quarter_from_text(period)
    result['financial_year'] = extract_financial_year(period)
    
    return result