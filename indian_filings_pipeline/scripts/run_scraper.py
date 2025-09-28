#!/usr/bin/env python3
"""
Main scraper execution script for Indian Filings Pipeline MVP
"""
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from src.database.connection import get_db_session, test_database_connection
from src.database.models import Company
from src.scrapers.nse_scraper import NSEScraper
from src.scrapers.bse_scraper import BSEScraper
from src.scrapers.screener_scraper import ScreenerScraper
from src.storage.file_manager import FileManager
from src.storage.document_store import DocumentStore
from src.utils.logger import setup_logging, get_logger, log_scraping_session

def load_companies(symbols: List[str] = None, limit: int = None) -> List[Company]:
    """Load companies from database"""
    logger = get_logger(__name__)
    
    try:
        with get_db_session() as session:
            query = session.query(Company).filter(Company.is_active == True)
            
            if symbols:
                query = query.filter(Company.symbol.in_(symbols))
            
            if limit:
                query = query.limit(limit)
            
            companies = query.all()
            
            # Detach objects from session to make them accessible outside the session
            for company in companies:
                session.expunge(company)
            
            logger.info(f"Loaded {len(companies)} companies for scraping")
            return companies
            
    except Exception as e:
        logger.error(f"Failed to load companies: {e}")
        return []

def run_scraper(scraper_class, companies: List[Company], scraper_name: str) -> Dict:
    """Run a specific scraper for given companies"""
    logger = get_logger(__name__)
    
    start_time = datetime.now()
    logger.info(f"Starting {scraper_name} scraper for {len(companies)} companies")
    
    # Create session log
    session_handler = log_scraping_session(scraper_name, len(companies), start_time)
    
    try:
        # Initialize scraper
        scraper = scraper_class()
        
        # Run scraper for all companies
        results = scraper.scrape_companies(companies)
        
        # Log final results
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"{scraper_name} completed in {execution_time:.2f} seconds")
        logger.info(f"Results: {results}")
        
        # Remove session handler
        scraper_logger = get_logger(f"scrapers.{scraper_name}")
        scraper_logger.removeHandler(session_handler)
        session_handler.close()
        
        return {
            'scraper': scraper_name,
            'execution_time': execution_time,
            'results': results,
            'status': 'success'
        }
        
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"{scraper_name} failed after {execution_time:.2f} seconds: {e}")
        
        # Remove session handler
        try:
            scraper_logger = get_logger(f"scrapers.{scraper_name}")
            scraper_logger.removeHandler(session_handler)
            session_handler.close()
        except:
            pass
        
        return {
            'scraper': scraper_name,
            'execution_time': execution_time,
            'error': str(e),
            'status': 'failed'
        }

def run_all_scrapers(companies: List[Company]) -> Dict:
    """Run all available scrapers"""
    logger = get_logger(__name__)
    
    scrapers = [
        (NSEScraper, 'nse_scraper'),
        (BSEScraper, 'bse_scraper'),
        (ScreenerScraper, 'screener_scraper')
    ]
    
    overall_results = {
        'start_time': datetime.now(),
        'scrapers': {},
        'summary': {
            'total_scrapers': len(scrapers),
            'successful_scrapers': 0,
            'failed_scrapers': 0,
            'total_companies_processed': 0,
            'total_documents_found': 0,
            'total_documents_downloaded': 0
        }
    }
    
    for scraper_class, scraper_name in scrapers:
        logger.info(f"Running {scraper_name}...")
        
        result = run_scraper(scraper_class, companies, scraper_name)
        overall_results['scrapers'][scraper_name] = result
        
        # Update summary
        if result['status'] == 'success':
            overall_results['summary']['successful_scrapers'] += 1
            scraper_results = result['results']
            overall_results['summary']['total_companies_processed'] += scraper_results.get('total_companies', 0)
            overall_results['summary']['total_documents_found'] += scraper_results.get('total_documents_found', 0)
            overall_results['summary']['total_documents_downloaded'] += scraper_results.get('total_documents_downloaded', 0)
        else:
            overall_results['summary']['failed_scrapers'] += 1
    
    overall_results['end_time'] = datetime.now()
    overall_results['total_execution_time'] = (
        overall_results['end_time'] - overall_results['start_time']
    ).total_seconds()
    
    return overall_results

def print_results_summary(results: Dict):
    """Print a formatted summary of scraping results"""
    print("\n" + "="*60)
    print("SCRAPING RESULTS SUMMARY")
    print("="*60)
    
    summary = results.get('summary', {})
    print(f"Total Execution Time: {results.get('total_execution_time', 0):.2f} seconds")
    print(f"Scrapers Run: {summary.get('total_scrapers', 0)}")
    print(f"Successful: {summary.get('successful_scrapers', 0)}")
    print(f"Failed: {summary.get('failed_scrapers', 0)}")
    print(f"Companies Processed: {summary.get('total_companies_processed', 0)}")
    print(f"Documents Found: {summary.get('total_documents_found', 0)}")
    print(f"Documents Downloaded: {summary.get('total_documents_downloaded', 0)}")
    
    print("\nPER-SCRAPER RESULTS:")
    print("-" * 40)
    
    for scraper_name, scraper_result in results.get('scrapers', {}).items():
        status = scraper_result.get('status', 'unknown')
        execution_time = scraper_result.get('execution_time', 0)
        
        print(f"{scraper_name.upper()}: {status.upper()} ({execution_time:.2f}s)")
        
        if status == 'success' and 'results' in scraper_result:
            scraper_stats = scraper_result['results']
            print(f"  - Companies: {scraper_stats.get('successful_companies', 0)}/{scraper_stats.get('total_companies', 0)}")
            print(f"  - Documents: {scraper_stats.get('total_documents_downloaded', 0)}/{scraper_stats.get('total_documents_found', 0)}")
        elif status == 'failed':
            print(f"  - Error: {scraper_result.get('error', 'Unknown error')}")
    
    print("\n" + "="*60)

def save_results_to_file(results: Dict, output_file: str):
    """Save results to JSON file"""
    try:
        # Convert datetime objects to strings for JSON serialization
        results_copy = results.copy()
        if 'start_time' in results_copy:
            results_copy['start_time'] = results_copy['start_time'].isoformat()
        if 'end_time' in results_copy:
            results_copy['end_time'] = results_copy['end_time'].isoformat()
        
        with open(output_file, 'w') as f:
            json.dump(results_copy, f, indent=2, default=str)
        
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to save results to file: {e}")

def validate_environment():
    """Validate that the environment is properly set up"""
    logger = get_logger(__name__)
    
    # Test database connection
    if not test_database_connection():
        logger.error("Database connection failed")
        return False
    
    # Check if directories exist
    if not settings.DOWNLOADS_DIR.exists():
        logger.error(f"Downloads directory does not exist: {settings.DOWNLOADS_DIR}")
        return False
    
    # Check if companies exist in database
    with get_db_session() as session:
        company_count = session.query(Company).count()
        if company_count == 0:
            logger.error("No companies found in database")
            return False
        
        logger.info(f"Environment validation passed: {company_count} companies in database")
    
    return True

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Run Indian Filings Pipeline Scrapers')
    parser.add_argument('--companies', nargs='+', help='Specific company symbols to scrape')
    parser.add_argument('--limit', type=int, help='Limit number of companies to process')
    parser.add_argument('--scraper', choices=['nse', 'bse', 'screener', 'all'], default='all', 
                       help='Which scraper to run')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Validate environment without running scrapers')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info("Starting Indian Filings Pipeline Scraper")
    logger.info(f"Arguments: {args}")
    
    try:
        # Validate environment
        if not validate_environment():
            print("❌ Environment validation failed")
            return 1
        
        if args.dry_run:
            print("✅ Environment validation passed (dry run mode)")
            return 0
        
        # Load companies
        companies = load_companies(symbols=args.companies, limit=args.limit)
        if not companies:
            print("❌ No companies to process")
            return 1
        
        print(f"📊 Processing {len(companies)} companies")
        
        # Run scrapers
        if args.scraper == 'all':
            results = run_all_scrapers(companies)
        elif args.scraper == 'nse':
            results = run_scraper(NSEScraper, companies, 'nse_scraper')
        elif args.scraper == 'bse':
            results = run_scraper(BSEScraper, companies, 'bse_scraper')
        elif args.scraper == 'screener':
            results = run_scraper(ScreenerScraper, companies, 'screener_scraper')
        
        # Print summary
        if args.scraper == 'all':
            print_results_summary(results)
        else:
            print(f"\n{args.scraper.upper()} Scraper Results:")
            print(f"Status: {results.get('status', 'unknown')}")
            print(f"Execution Time: {results.get('execution_time', 0):.2f} seconds")
            if 'results' in results:
                print(f"Results: {results['results']}")
        
        # Save results to file
        if args.output:
            save_results_to_file(results, args.output)
        
        # Check if any scrapers failed
        if args.scraper == 'all':
            if results['summary']['failed_scrapers'] > 0:
                print("⚠️  Some scrapers failed - check logs for details")
                return 1
        else:
            if results.get('status') != 'success':
                print("❌ Scraper failed - check logs for details")
                return 1
        
        print("✅ Scraping completed successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Scraping interrupted by user")
        logger.info("Scraping interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        logger.error(f"Scraping failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())