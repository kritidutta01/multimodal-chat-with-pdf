"""
Database models for the Indian Filings Pipeline
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

Base = declarative_base()

class Company(Base):
    """Company master data"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100))
    exchange = Column(String(10))  # NSE, BSE
    bse_code = Column(String(20))
    nse_symbol = Column(String(20))
    website = Column(String(255))
    ir_page = Column(String(255))  # Investor Relations page
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Additional company info (JSON field for flexibility)
    metadata_ = Column(JSON)
    
    # Relationships
    documents = relationship("Document", back_populates="company", cascade="all, delete-orphan")
    scraping_logs = relationship("ScrapingLog", back_populates="company")

    def __repr__(self):
        return f"<Company(symbol='{self.symbol}', name='{self.name}')>"

class Document(Base):
    """Document metadata and tracking"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    # Document identification
    title = Column(String(500))
    document_type = Column(String(50))  # annual_report, quarterly_result, presentation
    period = Column(String(20))  # FY2023, Q1FY2024, etc.
    year = Column(Integer)
    quarter = Column(String(5))  # Q1, Q2, Q3, Q4 (for quarterly docs)
    
    # File information
    filename = Column(String(255))
    file_path = Column(String(500))
    file_size = Column(Integer)  # in bytes
    file_hash = Column(String(64))  # SHA256 hash for deduplication
    file_extension = Column(String(10))
    
    # Source information
    source_url = Column(String(1000))
    source_platform = Column(String(50))  # NSE, BSE, company_website
    
    # Processing status
    download_status = Column(String(20), default="pending")  # pending, completed, failed
    processing_status = Column(String(20), default="pending")  # pending, completed, failed
    
    # Validation
    is_valid = Column(Boolean, default=True)
    validation_errors = Column(Text)
    
    # Timestamps
    published_date = Column(DateTime)  # When document was published by company
    discovered_at = Column(DateTime, default=func.now())  # When we found it
    downloaded_at = Column(DateTime)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Additional metadata (JSON field for flexibility)
    metadata_ = Column(JSON)
    
    # Relationships
    company = relationship("Company", back_populates="documents")
    document_chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', type='{self.document_type}')>"

class DocumentChunk(Base):
    """Text chunks extracted from documents (for LLM consumption)"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Chunk information
    chunk_index = Column(Integer)  # Order within document
    text_content = Column(Text)
    chunk_size = Column(Integer)  # Number of characters
    
    # Context information
    page_number = Column(Integer)
    section_title = Column(String(255))
    section_type = Column(String(50))  # financial_statement, notes, management_discussion
    
    # For overlapping chunks
    start_position = Column(Integer)
    end_position = Column(Integer)
    
    # Processing metadata
    extraction_method = Column(String(50))  # pymupdf, ocr, manual
    confidence_score = Column(Float)  # OCR confidence or validation score
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    # Additional metadata
    metadata_ = Column(JSON)
    
    # Relationships
    document = relationship("Document", back_populates="document_chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, doc_id={self.document_id}, index={self.chunk_index})>"

class ScrapingLog(Base):
    """Log of scraping activities"""
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    
    # Scraping details
    scraper_name = Column(String(50))  # nse_scraper, bse_scraper, etc.
    source_url = Column(String(1000))
    action = Column(String(50))  # discover, download, process
    status = Column(String(20))  # success, failed, partial
    
    # Results
    documents_found = Column(Integer, default=0)
    documents_downloaded = Column(Integer, default=0)
    documents_failed = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text)
    error_code = Column(String(20))
    
    # Performance metrics
    execution_time = Column(Float)  # in seconds
    response_time = Column(Float)  # in seconds
    
    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Additional metadata
    metadata_ = Column(JSON)
    
    # Relationships
    company = relationship("Company", back_populates="scraping_logs")

    def __repr__(self):
        return f"<ScrapingLog(id={self.id}, scraper='{self.scraper_name}', status='{self.status}')>"

class SystemConfig(Base):
    """System configuration and settings"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    config_type = Column(String(20))  # string, integer, boolean, json
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemConfig(key='{self.key}', value='{self.value}')>"