"""
Configuration settings for the Indian Filings Pipeline MVP
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Dict, Any

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database configuration
    DATABASE_URL: str = "sqlite:///data/indian_filings.db"
    
    # File storage paths
    BASE_DATA_DIR: Path = Path("data")
    DOWNLOADS_DIR: Path = BASE_DATA_DIR / "downloads"
    LOGS_DIR: Path = BASE_DATA_DIR / "logs"
    
    # Scraping configuration
    REQUEST_DELAY: float = 2.0  # Delay between requests in seconds
    REQUEST_TIMEOUT: int = 30   # Request timeout in seconds
    MAX_RETRIES: int = 3
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # File validation
    MIN_FILE_SIZE: int = 50 * 1024  # 50KB minimum file size
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB maximum file size
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".xls", ".xlsx", ".doc", ".docx"]
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Company data
    COMPANIES_FILE: Path = Path("config/companies.json")
    
    # URL patterns for different exchanges
    NSE_BASE_URL: str = "https://www.nseindia.com"
    BSE_BASE_URL: str = "https://www.bseindia.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

# Document type mappings
DOCUMENT_TYPES = {
    "annual_report": ["annual report", "annual", "yearly"],
    "quarterly_result": ["quarterly", "quarter", "q1", "q2", "q3", "q4"],
    "presentation": ["presentation", "investor", "ppt", "slides"],
    "financial_statement": ["financial", "statement", "balance sheet", "p&l"],
    "other": ["other", "miscellaneous"]
}

# Company sectors for the top 50 companies
COMPANY_SECTORS = {
    "Banking": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
    "IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"],
    "Oil & Gas": ["RELIANCE", "ONGC", "IOC", "BPCL", "GAIL"],
    "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR"],
    "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "BIOCON", "LUPIN"],
    "Auto": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO"],
    "Metals": ["TATASTEEL", "HINDALCO", "JINDALSTEL", "SAIL", "COALINDIA"],
    "Telecom": ["BHARTIARTL", "IDEA", "RCOM"],
    "Cement": ["ULTRACEMCO", "SHREECEM", "ACC", "AMBUJACEMENT"],
    "Conglomerate": ["ITC", "TATASTEEL", "ADANIGREEN"]
}

def create_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        settings.DOWNLOADS_DIR,
        settings.LOGS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        
def get_company_download_path(company_symbol: str, year: int, doc_type: str) -> Path:
    """Get the download path for a company document"""
    return settings.DOWNLOADS_DIR / company_symbol / str(year) / doc_type

def get_document_types() -> List[str]:
    """Get list of all document types"""
    return list(DOCUMENT_TYPES.keys())