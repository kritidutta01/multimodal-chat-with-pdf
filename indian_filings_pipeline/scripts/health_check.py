#!/usr/bin/env python3
"""
Health check script for the Indian Filings Pipeline
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.connection import test_database_connection, get_table_stats
from config.settings import settings

def check_database():
    """Check SQLite database connectivity and basic functionality"""
    try:
        if not test_database_connection():
            return False, "SQLite database connection failed"
        
        stats = get_table_stats()
        if not stats:
            return False, "Unable to get table statistics"
        
        # Check database file exists and is writable
        from config.settings import settings
        if settings.DATABASE_URL.startswith('sqlite:///'):
            db_path = Path(settings.DATABASE_URL.replace('sqlite:///', ''))
            if not db_path.exists():
                return False, f"Database file does not exist: {db_path}"
            
            # Check if we can write to the database directory
            db_dir = db_path.parent
            if not db_dir.exists():
                return False, f"Database directory does not exist: {db_dir}"
        
        return True, f"SQLite database OK - {stats}"
    except Exception as e:
        return False, f"Database check failed: {e}"

def check_file_system():
    """Check file system directories and permissions"""
    try:
        # Check if required directories exist and are writable
        directories_to_check = [
            settings.DOWNLOADS_DIR,
            settings.LOGS_DIR,
        ]
        
        for directory in directories_to_check:
            if not directory.exists():
                return False, f"Directory does not exist: {directory}"
            
            # Try to create a test file
            test_file = directory / "health_check_test.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                return False, f"Cannot write to directory {directory}: {e}"
        
        return True, "File system OK"
    except Exception as e:
        return False, f"File system check failed: {e}"

def check_dependencies():
    """Check if required Python packages are available"""
    try:
        required_packages = [
            'requests',
            'beautifulsoup4',
            'sqlalchemy',
            'psycopg2',
            'fitz',  # PyMuPDF
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            return False, f"Missing packages: {missing_packages}"
        
        return True, "Dependencies OK"
    except Exception as e:
        return False, f"Dependencies check failed: {e}"

def main():
    """Run all health checks"""
    print("Running Indian Filings Pipeline Health Check...")
    
    checks = [
        ("Database", check_database),
        ("File System", check_file_system),
        ("Dependencies", check_dependencies),
    ]
    
    all_passed = True
    results = []
    
    for check_name, check_function in checks:
        try:
            passed, message = check_function()
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{check_name}: {status} - {message}")
            results.append((check_name, passed, message))
            
            if not passed:
                all_passed = False
                
        except Exception as e:
            print(f"{check_name}: ❌ ERROR - {e}")
            results.append((check_name, False, str(e)))
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 All health checks passed!")
        return 0
    else:
        print("💥 Some health checks failed!")
        print("\nFailed checks:")
        for name, passed, message in results:
            if not passed:
                print(f"  - {name}: {message}")
        return 1

if __name__ == "__main__":
    sys.exit(main())