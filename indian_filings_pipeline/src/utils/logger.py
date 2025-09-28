"""
Logging configuration and utilities
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

from config.settings import settings

def setup_logging():
    """Setup logging configuration for the application"""
    
    # Create logs directory if it doesn't exist
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    all_logs_file = settings.LOGS_DIR / 'pipeline.log'
    file_handler = logging.handlers.RotatingFileHandler(
        all_logs_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_logs_file = settings.LOGS_DIR / 'errors.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_logs_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Scraper specific handler
    scraper_logs_file = settings.LOGS_DIR / 'scrapers.log'
    scraper_handler = logging.handlers.RotatingFileHandler(
        scraper_logs_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    scraper_handler.setLevel(logging.DEBUG)
    scraper_handler.setFormatter(detailed_formatter)
    
    # Add scraper handler to scraper loggers
    scraper_logger = logging.getLogger('src.scrapers')
    scraper_logger.addHandler(scraper_handler)
    
    # Set specific log levels for third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    logging.info("Logging configuration completed")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)

def log_scraping_session(scraper_name: str, company_count: int, start_time: datetime):
    """Log the start of a scraping session"""
    logger = get_logger(f"scrapers.{scraper_name}")
    logger.info(f"Starting scraping session: {company_count} companies to process")
    
    # Create session-specific log file
    session_id = start_time.strftime("%Y%m%d_%H%M%S")
    session_log_file = settings.LOGS_DIR / f"session_{scraper_name}_{session_id}.log"
    
    session_handler = logging.FileHandler(session_log_file)
    session_handler.setLevel(logging.DEBUG)
    session_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    session_handler.setFormatter(session_formatter)
    
    logger.addHandler(session_handler)
    logger.info(f"Session log file: {session_log_file}")
    
    return session_handler

def log_company_processing(company_symbol: str, action: str, status: str, **kwargs):
    """Log company processing activities"""
    logger = get_logger("scrapers.company")
    
    extra_info = ""
    if kwargs:
        extra_info = f" - {', '.join([f'{k}: {v}' for k, v in kwargs.items()])}"
    
    message = f"Company: {company_symbol} | Action: {action} | Status: {status}{extra_info}"
    
    if status == 'success':
        logger.info(message)
    elif status == 'failed':
        logger.error(message)
    else:
        logger.debug(message)

def log_document_processing(document_title: str, action: str, status: str, **kwargs):
    """Log document processing activities"""
    logger = get_logger("processing.documents")
    
    extra_info = ""
    if kwargs:
        extra_info = f" - {', '.join([f'{k}: {v}' for k, v in kwargs.items()])}"
    
    message = f"Document: {document_title} | Action: {action} | Status: {status}{extra_info}"
    
    if status == 'success':
        logger.info(message)
    elif status == 'failed':
        logger.error(message)
    else:
        logger.debug(message)

def log_performance_metrics(operation: str, execution_time: float, **metrics):
    """Log performance metrics"""
    logger = get_logger("performance")
    
    metrics_str = ', '.join([f'{k}: {v}' for k, v in metrics.items()])
    message = f"Operation: {operation} | Execution Time: {execution_time:.2f}s | Metrics: {metrics_str}"
    
    logger.info(message)

def log_database_operation(operation: str, table: str, count: int, execution_time: float):
    """Log database operations"""
    logger = get_logger("database")
    
    message = f"DB Operation: {operation} | Table: {table} | Records: {count} | Time: {execution_time:.3f}s"
    logger.debug(message)

def create_daily_log_summary():
    """Create a daily summary of log activities"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        summary_file = settings.LOGS_DIR / f"summary_{today}.log"
        
        # Count log entries by level from today's logs
        log_files = [
            settings.LOGS_DIR / 'pipeline.log',
            settings.LOGS_DIR / 'scrapers.log',
            settings.LOGS_DIR / 'errors.log'
        ]
        
        summary_stats = {
            'INFO': 0,
            'WARNING': 0,
            'ERROR': 0,
            'DEBUG': 0
        }
        
        for log_file in log_files:
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        if today in line:
                            for level in summary_stats.keys():
                                if f" {level} " in line:
                                    summary_stats[level] += 1
                                    break
        
        # Write summary
        with open(summary_file, 'w') as f:
            f.write(f"Daily Log Summary for {today}\n")
            f.write("=" * 40 + "\n")
            for level, count in summary_stats.items():
                f.write(f"{level}: {count}\n")
        
        logger = get_logger("summary")
        logger.info(f"Daily log summary created: {summary_file}")
        
    except Exception as e:
        logger = get_logger("summary")
        logger.error(f"Failed to create daily log summary: {e}")

# Exception logging decorator
def log_exceptions(logger_name: str = None):
    """Decorator to log exceptions in functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Exception in {func.__name__}: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator