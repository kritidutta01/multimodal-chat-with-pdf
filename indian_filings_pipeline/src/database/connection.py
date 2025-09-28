"""
Database connection and session management for SQLite
"""
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator, Optional
from pathlib import Path

from config.settings import settings
from .models import Base
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection and session manager for SQLite"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize SQLite database engine with proper configuration"""
        try:
            # Ensure database directory exists
            if self.database_url.startswith('sqlite:///'):
                db_path = Path(self.database_url.replace('sqlite:///', ''))
                db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create engine with SQLite-specific configuration
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                echo=False,          # Set to True for SQL logging in development
                connect_args={"check_same_thread": False}  # Allow SQLite to be used with threads
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Add connection event listeners for SQLite
            event.listen(self.engine, "connect", self._on_connect_sqlite)
            
            logger.info("SQLite database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def _on_connect_sqlite(self, dbapi_connection, connection_record):
        """Called when a new SQLite database connection is created"""
        # Enable foreign key constraint checking in SQLite
        dbapi_connection.execute('PRAGMA foreign_keys=ON')
        # Set journal mode to WAL for better concurrent access
        dbapi_connection.execute('PRAGMA journal_mode=WAL')
        # Set synchronous mode to NORMAL for better performance
        dbapi_connection.execute('PRAGMA synchronous=NORMAL')
        logger.debug("New SQLite database connection established with optimized settings")
    
    def create_tables(self):
        """Create all tables in the database"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all tables in the database (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """Get a database session (manual management required)"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def close(self):
        """Close database engine and all connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine closed")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
def get_db_session():
    """Get database session context manager"""
    return db_manager.get_session()

def get_db():
    """Get database session (for dependency injection)"""
    return db_manager.get_session_direct()

def init_database():
    """Initialize database and create tables"""
    try:
        db_manager.create_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    return db_manager.test_connection()

# Database utility functions
def execute_sql_file(sql_file_path: str):
    """Execute SQL commands from a file"""
    try:
        with open(sql_file_path, 'r') as file:
            sql_commands = file.read()
        
        with db_manager.get_session() as session:
            # Split by semicolon and execute each command
            for command in sql_commands.split(';'):
                command = command.strip()
                if command:
                    session.execute(command)
        
        logger.info(f"SQL file executed successfully: {sql_file_path}")
        
    except Exception as e:
        logger.error(f"Failed to execute SQL file {sql_file_path}: {e}")
        raise

def get_table_stats():
    """Get basic statistics about database tables"""
    stats = {}
    try:
        with db_manager.get_session() as session:
            # Count records in each table
            from .models import Company, Document, DocumentChunk, ScrapingLog
            
            stats['companies'] = session.query(Company).count()
            stats['documents'] = session.query(Document).count()
            stats['document_chunks'] = session.query(DocumentChunk).count()
            stats['scraping_logs'] = session.query(ScrapingLog).count()
            
        logger.info(f"Database stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get table stats: {e}")
        return {}

def cleanup_old_logs(days: int = 30):
    """Clean up old scraping logs"""
    try:
        from datetime import datetime, timedelta
        from .models import ScrapingLog
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with db_manager.get_session() as session:
            deleted_count = session.query(ScrapingLog).filter(
                ScrapingLog.created_at < cutoff_date
            ).delete()
            
        logger.info(f"Cleaned up {deleted_count} old scraping logs")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup old logs: {e}")
        return 0

def get_database_size():
    """Get SQLite database file size"""
    try:
        if db_manager.database_url.startswith('sqlite:///'):
            db_path = Path(db_manager.database_url.replace('sqlite:///', ''))
            if db_path.exists():
                size_bytes = db_path.stat().st_size
                size_mb = size_bytes / (1024 * 1024)
                return {'size_bytes': size_bytes, 'size_mb': round(size_mb, 2)}
        return {'size_bytes': 0, 'size_mb': 0}
    except Exception as e:
        logger.error(f"Failed to get database size: {e}")
        return {'size_bytes': 0, 'size_mb': 0}