"""
Validation utilities for file and data validation
"""
import magic
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from config.settings import settings

logger = logging.getLogger(__name__)

def validate_file_size(file_size: int) -> bool:
    """Validate if file size is within acceptable limits"""
    if file_size < settings.MIN_FILE_SIZE:
        logger.warning(f"File too small: {file_size} bytes (minimum: {settings.MIN_FILE_SIZE})")
        return False
    
    if file_size > settings.MAX_FILE_SIZE:
        logger.warning(f"File too large: {file_size} bytes (maximum: {settings.MAX_FILE_SIZE})")
        return False
    
    return True

def validate_file_type(file_path: str, allowed_extensions: Optional[List[str]] = None) -> bool:
    """Validate file type based on extension and MIME type"""
    if allowed_extensions is None:
        allowed_extensions = settings.ALLOWED_EXTENSIONS
    
    try:
        file_path = Path(file_path)
        
        # Check file extension
        extension = file_path.suffix.lower()
        if extension not in allowed_extensions:
            logger.warning(f"Invalid file extension: {extension}")
            return False
        
        # Check MIME type using python-magic
        if file_path.exists():
            mime_type = magic.from_file(str(file_path), mime=True)
            
            # Define expected MIME types for each extension
            expected_mime_types = {
                '.pdf': ['application/pdf'],
                '.xls': ['application/vnd.ms-excel'],
                '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
                '.doc': ['application/msword'],
                '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            }
            
            if extension in expected_mime_types:
                if mime_type not in expected_mime_types[extension]:
                    logger.warning(f"MIME type mismatch: expected {expected_mime_types[extension]}, got {mime_type}")
                    return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating file type: {e}")
        return False

def validate_pdf_content(file_path: str) -> Tuple[bool, Optional[str]]:
    """Validate PDF file content and readability"""
    try:
        import fitz  # PyMuPDF
        
        # Try to open and read the PDF
        doc = fitz.open(file_path)
        
        # Check if PDF has any pages
        if len(doc) == 0:
            return False, "PDF has no pages"
        
        # Try to extract text from first page
        first_page = doc[0]
        text = first_page.get_text()
        
        # Check if PDF contains readable text
        if not text.strip():
            # Try OCR if no text found (for scanned PDFs)
            # This is a basic check - OCR would be implemented later
            logger.info(f"PDF appears to be scanned (no extractable text): {file_path}")
        
        doc.close()
        return True, None
        
    except Exception as e:
        error_msg = f"PDF validation failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def validate_excel_content(file_path: str) -> Tuple[bool, Optional[str]]:
    """Validate Excel file content and readability"""
    try:
        import pandas as pd
        
        # Try to read the Excel file
        excel_file = pd.ExcelFile(file_path)
        
        # Check if file has any sheets
        if not excel_file.sheet_names:
            return False, "Excel file has no sheets"
        
        # Try to read first sheet
        first_sheet = pd.read_excel(file_path, sheet_name=0, nrows=5)
        
        return True, None
        
    except Exception as e:
        error_msg = f"Excel validation failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def validate_document_content(file_path: str) -> Tuple[bool, Optional[str]]:
    """Validate document content based on file type"""
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    if extension == '.pdf':
        return validate_pdf_content(str(file_path))
    elif extension in ['.xls', '.xlsx']:
        return validate_excel_content(str(file_path))
    else:
        # For other file types, just check if file exists and is readable
        try:
            with open(file_path, 'rb') as f:
                # Try to read first 1KB
                f.read(1024)
            return True, None
        except Exception as e:
            return False, f"File read error: {str(e)}"

def validate_url(url: str) -> bool:
    """Validate URL format"""
    import re
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None

def validate_company_symbol(symbol: str) -> bool:
    """Validate company symbol format"""
    if not symbol:
        return False
    
    # Company symbols are usually alphanumeric with some special characters
    import re
    pattern = re.compile(r'^[A-Z0-9&\-\.]+$')
    return bool(pattern.match(symbol.upper()))

def validate_date_string(date_str: str) -> bool:
    """Validate date string format"""
    if not date_str:
        return False
    
    from datetime import datetime
    
    # Common date formats
    date_formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y/%m/%d',
        '%d %B %Y',
        '%d %b %Y',
        '%B %d, %Y',
        '%b %d, %Y'
    ]
    
    for date_format in date_formats:
        try:
            datetime.strptime(date_str, date_format)
            return True
        except ValueError:
            continue
    
    return False

def validate_financial_year(fy_str: str) -> bool:
    """Validate financial year format"""
    if not fy_str:
        return False
    
    import re
    
    # FY patterns: FY2024, FY24, FY2023-24, FY23-24
    fy_patterns = [
        r'^FY\d{4}$',
        r'^FY\d{2}$',
        r'^FY\d{4}-\d{2}$',
        r'^FY\d{2}-\d{2}$'
    ]
    
    for pattern in fy_patterns:
        if re.match(pattern, fy_str.upper()):
            return True
    
    return False

def validate_quarter(quarter_str: str) -> bool:
    """Validate quarter format"""
    if not quarter_str:
        return False
    
    valid_quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    return quarter_str.upper() in valid_quarters

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove problematic characters"""
    import re
    
    # Remove or replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not too long
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_length] + ('.' + ext if ext else '')
    
    return filename

def check_duplicate_content(file_hash: str, existing_hashes: List[str]) -> bool:
    """Check if file content is duplicate based on hash"""
    return file_hash in existing_hashes

def validate_document_metadata(metadata: dict) -> Tuple[bool, List[str]]:
    """Validate document metadata completeness"""
    errors = []
    required_fields = ['title', 'document_type', 'source_url']
    
    for field in required_fields:
        if field not in metadata or not metadata[field]:
            errors.append(f"Missing required field: {field}")
    
    # Validate specific fields
    if 'source_url' in metadata and not validate_url(metadata['source_url']):
        errors.append("Invalid source URL format")
    
    if 'published_date' in metadata and metadata['published_date']:
        if not validate_date_string(str(metadata['published_date'])):
            errors.append("Invalid published date format")
    
    if 'financial_year' in metadata and metadata['financial_year']:
        if not validate_financial_year(metadata['financial_year']):
            errors.append("Invalid financial year format")
    
    if 'quarter' in metadata and metadata['quarter']:
        if not validate_quarter(metadata['quarter']):
            errors.append("Invalid quarter format")
    
    return len(errors) == 0, errors