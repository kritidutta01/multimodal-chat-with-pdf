#!/usr/bin/env python3
"""
Database setup script for Indian Filings Pipeline MVP
"""
import sys
import json
import logging
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings, create_directories
from src.database.connection import init_database, test_database_connection, get_db_session
from src.database.models import Company, SystemConfig
from src.utils.logger import setup_logging, get_logger

def load_companies_data():
    """Load companies from JSON file"""
    try:
        with open(settings.COMPANIES_FILE, 'r') as f:
            data = json.load(f)
        return data.get('companies', [])
    except Exception as e:
        logger.error(f"Failed to load companies data: {e}")
        return []

def populate_companies(companies_data):
    """Populate companies table with initial data"""
    logger = get_logger(__name__)
    
    try:
        with get_db_session() as session:
            # Check if companies already exist
            existing_count = session.query(Company).count()
            if existing_count > 0:
                logger.info(f"Companies table already has {existing_count} records")
                return existing_count
            
            # Insert companies
            companies_added = 0
            for company_data in companies_data:
                try:
                    company = Company(
                        symbol=company_data['symbol'],
                        name=company_data['name'],
                        sector=company_data['sector'],
                        exchange=company_data['exchange'],
                        bse_code=company_data.get('bse_code'),
                        nse_symbol=company_data.get('nse_symbol'),
                        website=company_data.get('website'),
                        ir_page=company_data.get('ir_page'),
                        metadata={
                            'initial_data': company_data
                        }
                    )
                    session.add(company)
                    companies_added += 1
                    logger.debug(f"Added company: {company.symbol}")
                    
                except Exception as e:
                    logger.error(f"Failed to add company {company_data.get('symbol', 'Unknown')}: {e}")
                    continue
            
            session.commit()
            logger.info(f"Successfully added {companies_added} companies to database")
            return companies_added
            
    except Exception as e:
        logger.error(f"Failed to populate companies: {e}")
        return 0

def setup_system_config():
    """Setup initial system configuration"""
    logger = get_logger(__name__)
    
    initial_config = [
        {
            'key': 'last_scraping_run',
            'value': '',
            'description': 'Timestamp of last scraping run',
            'config_type': 'string'
        },
        {
            'key': 'scraping_enabled',
            'value': 'true',
            'description': 'Enable/disable scraping operations',
            'config_type': 'boolean'
        },
        {
            'key': 'max_concurrent_scrapers',
            'value': '1',
            'description': 'Maximum number of concurrent scrapers',
            'config_type': 'integer'
        },
        {
            'key': 'pipeline_version',
            'value': '1.0.0',
            'description': 'Pipeline version',
            'config_type': 'string'
        }
    ]
    
    try:
        with get_db_session() as session:
            configs_added = 0
            
            for config_data in initial_config:
                # Check if config already exists
                existing = session.query(SystemConfig).filter(
                    SystemConfig.key == config_data['key']
                ).first()
                
                if not existing:
                    config = SystemConfig(**config_data)
                    session.add(config)
                    configs_added += 1
                    logger.debug(f"Added config: {config.key}")
            
            session.commit()
            logger.info(f"Added {configs_added} system configuration entries")
            return configs_added
            
    except Exception as e:
        logger.error(f"Failed to setup system config: {e}")
        return 0

def create_sample_directories():
    """Create sample directory structure"""
    logger = get_logger(__name__)
    
    try:
        # Create main directories
        create_directories()
        
        # Create sample company directories
        sample_companies = ['RELIANCE', 'TCS', 'HDFCBANK']
        current_year = 2024
        
        for company in sample_companies:
            for year in [current_year - 1, current_year]:
                for doc_type in ['annual_reports', 'quarterly_results', 'presentations']:
                    dir_path = settings.DOWNLOADS_DIR / company / str(year) / doc_type
                    dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Sample directory structure created")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        return False

def verify_setup():
    """Verify database setup"""
    logger = get_logger(__name__)
    
    try:
        with get_db_session() as session:
            # Check tables
            tables_stats = {
                'companies': session.query(Company).count(),
                'system_config': session.query(SystemConfig).count(),
            }
            
            logger.info("Database setup verification:")
            for table, count in tables_stats.items():
                logger.info(f"  {table}: {count} records")
            
            # Test some basic queries
            if tables_stats['companies'] > 0:
                sample_company = session.query(Company).first()
                logger.info(f"Sample company: {sample_company.symbol} - {sample_company.name}")
            
            return all(count > 0 for count in tables_stats.values())
            
    except Exception as e:
        logger.error(f"Setup verification failed: {e}")
        return False

def main():
    """Main setup function"""
    print("Setting up Indian Filings Pipeline Database...")
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("Starting database setup")
    
    try:
        # Test database connection
        print("1. Testing SQLite database connection...")
        if not test_database_connection():
            print("❌ Database connection failed")
            logger.error("Database connection test failed")
            return False
        print("✅ SQLite database connection successful")
        
        # Initialize database (create tables)
        print("2. Creating database tables...")
        if not init_database():
            print("❌ Database initialization failed")
            logger.error("Database initialization failed")
            return False
        print("✅ Database tables created")
        
        # Load and populate companies
        print("3. Loading company data...")
        companies_data = load_companies_data()
        if not companies_data:
            print("❌ Failed to load companies data")
            logger.error("No companies data loaded")
            return False
        print(f"✅ Loaded {len(companies_data)} companies")
        
        print("4. Populating companies table...")
        companies_added = populate_companies(companies_data)
        print(f"✅ Added {companies_added} companies to database")
        
        # Setup system configuration
        print("5. Setting up system configuration...")
        configs_added = setup_system_config()
        print(f"✅ Added {configs_added} configuration entries")
        
        # Create directories
        print("6. Creating directory structure...")
        if create_sample_directories():
            print("✅ Directory structure created")
        else:
            print("⚠️ Warning: Directory creation had issues")
        
        # Verify setup
        print("7. Verifying setup...")
        if verify_setup():
            print("✅ Setup verification passed")
        else:
            print("❌ Setup verification failed")
            return False
        
        print("\n🎉 Database setup completed successfully!")
        print(f"📁 Data directory: {settings.DOWNLOADS_DIR}")
        print(f"📋 Log directory: {settings.LOGS_DIR}")
        print(f"🏢 Companies loaded: {companies_added}")
        
        logger.info("Database setup completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        logger.error(f"Setup failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)