"""
Document storage and retrieval operations
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.database.models import Company, Document, DocumentChunk, ScrapingLog
from src.utils.helpers import parse_period_string

logger = logging.getLogger(__name__)

class DocumentStore:
    """Handles database operations for documents"""
    
    def __init__(self):
        pass
    
    def save_document(self, company_id: int, document_data: Dict) -> Optional[Document]:
        """Save document metadata to database"""
        try:
            with get_db_session() as session:
                # Check if document already exists (by hash)
                if 'file_hash' in document_data:
                    existing = session.query(Document).filter(
                        and_(
                            Document.company_id == company_id,
                            Document.file_hash == document_data['file_hash']
                        )
                    ).first()
                    
                    if existing:
                        logger.info(f"Document already exists: {existing.id}")
                        return existing
                
                # Create new document
                document = Document(
                    company_id=company_id,
                    title=document_data.get('title'),
                    document_type=document_data.get('document_type'),
                    period=document_data.get('period'),
                    year=document_data.get('year'),
                    quarter=document_data.get('quarter'),
                    filename=document_data.get('filename'),
                    file_path=document_data.get('file_path'),
                    file_size=document_data.get('file_size'),
                    file_hash=document_data.get('file_hash'),
                    file_extension=document_data.get('file_extension'),
                    source_url=document_data.get('source_url'),
                    source_platform=document_data.get('source_platform'),
                    download_status=document_data.get('download_status', 'completed'),
                    processing_status=document_data.get('processing_status', 'pending'),
                    is_valid=document_data.get('is_valid', True),
                    validation_errors=document_data.get('validation_errors'),
                    published_date=document_data.get('published_date'),
                    downloaded_at=document_data.get('downloaded_at', datetime.now()),
                    metadata=document_data.get('metadata', {})
                )
                
                session.add(document)
                session.flush()  # To get the ID
                
                logger.info(f"Document saved to database: {document.id}")
                return document
                
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return None
    
    def get_document_by_id(self, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        try:
            with get_db_session() as session:
                return session.query(Document).filter(Document.id == document_id).first()
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    def get_documents_by_company(self, company_id: int, limit: int = None) -> List[Document]:
        """Get all documents for a company"""
        try:
            with get_db_session() as session:
                query = session.query(Document).filter(Document.company_id == company_id)
                query = query.order_by(desc(Document.published_date), desc(Document.downloaded_at))
                
                if limit:
                    query = query.limit(limit)
                
                return query.all()
        except Exception as e:
            logger.error(f"Failed to get documents for company {company_id}: {e}")
            return []
    
    def get_documents_by_type(self, document_type: str, company_id: Optional[int] = None) -> List[Document]:
        """Get documents by type"""
        try:
            with get_db_session() as session:
                query = session.query(Document).filter(Document.document_type == document_type)
                
                if company_id:
                    query = query.filter(Document.company_id == company_id)
                
                query = query.order_by(desc(Document.published_date))
                return query.all()
        except Exception as e:
            logger.error(f"Failed to get documents by type {document_type}: {e}")
            return []
    
    def search_documents(self, search_params: Dict) -> List[Document]:
        """Search documents with various filters"""
        try:
            with get_db_session() as session:
                query = session.query(Document)
                
                # Apply filters
                if 'company_id' in search_params:
                    query = query.filter(Document.company_id == search_params['company_id'])
                
                if 'company_symbol' in search_params:
                    query = query.join(Company).filter(
                        Company.symbol == search_params['company_symbol']
                    )
                
                if 'document_type' in search_params:
                    query = query.filter(Document.document_type == search_params['document_type'])
                
                if 'year' in search_params:
                    query = query.filter(Document.year == search_params['year'])
                
                if 'quarter' in search_params:
                    query = query.filter(Document.quarter == search_params['quarter'])
                
                if 'period' in search_params:
                    query = query.filter(Document.period.ilike(f"%{search_params['period']}%"))
                
                if 'title' in search_params:
                    query = query.filter(Document.title.ilike(f"%{search_params['title']}%"))
                
                if 'source_platform' in search_params:
                    query = query.filter(Document.source_platform == search_params['source_platform'])
                
                if 'date_from' in search_params:
                    query = query.filter(Document.published_date >= search_params['date_from'])
                
                if 'date_to' in search_params:
                    query = query.filter(Document.published_date <= search_params['date_to'])
                
                if 'download_status' in search_params:
                    query = query.filter(Document.download_status == search_params['download_status'])
                
                if 'processing_status' in search_params:
                    query = query.filter(Document.processing_status == search_params['processing_status'])
                
                # Sorting
                sort_by = search_params.get('sort_by', 'published_date')
                sort_order = search_params.get('sort_order', 'desc')
                
                if hasattr(Document, sort_by):
                    if sort_order == 'asc':
                        query = query.order_by(asc(getattr(Document, sort_by)))
                    else:
                        query = query.order_by(desc(getattr(Document, sort_by)))
                
                # Pagination
                if 'limit' in search_params:
                    query = query.limit(search_params['limit'])
                
                if 'offset' in search_params:
                    query = query.offset(search_params['offset'])
                
                return query.all()
                
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    def update_document_status(self, document_id: int, status_updates: Dict) -> bool:
        """Update document status fields"""
        try:
            with get_db_session() as session:
                document = session.query(Document).filter(Document.id == document_id).first()
                
                if not document:
                    logger.warning(f"Document not found: {document_id}")
                    return False
                
                # Update allowed status fields
                allowed_fields = [
                    'download_status', 'processing_status', 'is_valid',
                    'validation_errors', 'processed_at', 'metadata'
                ]
                
                for field, value in status_updates.items():
                    if field in allowed_fields and hasattr(document, field):
                        setattr(document, field, value)
                
                document.updated_at = datetime.now()
                
                logger.info(f"Document status updated: {document_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update document status {document_id}: {e}")
            return False
    
    def get_duplicate_documents(self) -> Dict[str, List[Document]]:
        """Find documents with duplicate content (same hash)"""
        try:
            with get_db_session() as session:
                # Get documents grouped by hash
                duplicates = {}
                
                documents = session.query(Document).filter(
                    Document.file_hash.isnot(None)
                ).all()
                
                hash_groups = {}
                for doc in documents:
                    if doc.file_hash not in hash_groups:
                        hash_groups[doc.file_hash] = []
                    hash_groups[doc.file_hash].append(doc)
                
                # Filter to only groups with duplicates
                for file_hash, docs in hash_groups.items():
                    if len(docs) > 1:
                        duplicates[file_hash] = docs
                
                logger.info(f"Found {len(duplicates)} groups of duplicate documents")
                return duplicates
                
        except Exception as e:
            logger.error(f"Failed to find duplicate documents: {e}")
            return {}
    
    def delete_document(self, document_id: int) -> bool:
        """Delete document from database"""
        try:
            with get_db_session() as session:
                document = session.query(Document).filter(Document.id == document_id).first()
                
                if not document:
                    logger.warning(f"Document not found for deletion: {document_id}")
                    return False
                
                session.delete(document)
                logger.info(f"Document deleted from database: {document_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    def get_company_document_stats(self, company_id: int) -> Dict:
        """Get document statistics for a company"""
        try:
            with get_db_session() as session:
                # Basic counts
                total_docs = session.query(Document).filter(Document.company_id == company_id).count()
                
                # By document type
                type_counts = {}
                type_results = session.query(
                    Document.document_type,
                    session.query(Document).filter(
                        and_(Document.company_id == company_id, 
                             Document.document_type == Document.document_type)
                    ).count().label('count')
                ).filter(Document.company_id == company_id).distinct().all()
                
                for doc_type, count in type_results:
                    type_counts[doc_type] = count
                
                # By year
                year_counts = {}
                year_results = session.query(
                    Document.year,
                    session.query(Document).filter(
                        and_(Document.company_id == company_id,
                             Document.year == Document.year)
                    ).count().label('count')
                ).filter(
                    and_(Document.company_id == company_id, Document.year.isnot(None))
                ).distinct().all()
                
                for year, count in year_results:
                    year_counts[year] = count
                
                # By status
                status_counts = {
                    'completed': session.query(Document).filter(
                        and_(Document.company_id == company_id,
                             Document.download_status == 'completed')
                    ).count(),
                    'failed': session.query(Document).filter(
                        and_(Document.company_id == company_id,
                             Document.download_status == 'failed')
                    ).count(),
                    'pending': session.query(Document).filter(
                        and_(Document.company_id == company_id,
                             Document.download_status == 'pending')
                    ).count()
                }
                
                # File size stats
                total_size = session.query(
                    session.query(Document.file_size).filter(
                        Document.company_id == company_id
                    ).filter(Document.file_size.isnot(None))
                ).scalar() or 0
                
                return {
                    'company_id': company_id,
                    'total_documents': total_docs,
                    'by_type': type_counts,
                    'by_year': year_counts,
                    'by_status': status_counts,
                    'total_size_bytes': total_size
                }
                
        except Exception as e:
            logger.error(f"Failed to get document stats for company {company_id}: {e}")
            return {}
    
    def get_recent_documents(self, limit: int = 10) -> List[Document]:
        """Get recently downloaded documents"""
        try:
            with get_db_session() as session:
                return session.query(Document).order_by(
                    desc(Document.downloaded_at)
                ).limit(limit).all()
        except Exception as e:
            logger.error(f"Failed to get recent documents: {e}")
            return []
    
    def get_processing_queue(self, status: str = 'pending', limit: int = None) -> List[Document]:
        """Get documents in processing queue"""
        try:
            with get_db_session() as session:
                query = session.query(Document).filter(
                    Document.processing_status == status
                ).order_by(Document.downloaded_at)
                
                if limit:
                    query = query.limit(limit)
                
                return query.all()
        except Exception as e:
            logger.error(f"Failed to get processing queue: {e}")
            return []
    
    def save_document_chunks(self, document_id: int, chunks: List[Dict]) -> bool:
        """Save document text chunks for LLM processing"""
        try:
            with get_db_session() as session:
                # Delete existing chunks for this document
                session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id
                ).delete()
                
                # Add new chunks
                for i, chunk_data in enumerate(chunks):
                    chunk = DocumentChunk(
                        document_id=document_id,
                        chunk_index=i,
                        text_content=chunk_data.get('text_content'),
                        chunk_size=len(chunk_data.get('text_content', '')),
                        page_number=chunk_data.get('page_number'),
                        section_title=chunk_data.get('section_title'),
                        section_type=chunk_data.get('section_type'),
                        start_position=chunk_data.get('start_position'),
                        end_position=chunk_data.get('end_position'),
                        extraction_method=chunk_data.get('extraction_method'),
                        confidence_score=chunk_data.get('confidence_score'),
                        metadata=chunk_data.get('metadata', {})
                    )
                    session.add(chunk)
                
                logger.info(f"Saved {len(chunks)} chunks for document {document_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save document chunks for {document_id}: {e}")
            return False
    
    def get_document_chunks(self, document_id: int) -> List[DocumentChunk]:
        """Get text chunks for a document"""
        try:
            with get_db_session() as session:
                return session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id
                ).order_by(DocumentChunk.chunk_index).all()
        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {e}")
            return []