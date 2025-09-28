"""
File management utilities for document storage and organization
"""
import os
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from config.settings import settings, get_company_download_path
from src.utils.validators import validate_file_size, validate_file_type, validate_document_content
from src.utils.helpers import format_file_size 
from src.utils.validators import sanitize_filename

logger = logging.getLogger(__name__)

class FileManager:
    """Manages file operations for downloaded documents"""
    
    def __init__(self):
        self.base_dir = settings.DOWNLOADS_DIR
        self.ensure_base_directory()
    
    def ensure_base_directory(self):
        """Ensure base download directory exists"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Base directory ensured: {self.base_dir}")
    
    def get_company_directory(self, company_symbol: str, year: int, doc_type: str) -> Path:
        """Get the directory path for a company's documents"""
        company_dir = get_company_download_path(company_symbol, year, doc_type)
        company_dir.mkdir(parents=True, exist_ok=True)
        return company_dir
    
    def save_document(self, content: bytes, company_symbol: str, filename: str, 
                     year: int, doc_type: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Save document content to file system
        
        Returns:
            Tuple of (success, file_path, file_info)
        """
        try:
            # Sanitize filename
            clean_filename = sanitize_filename(filename)
            
            # Get target directory
            target_dir = self.get_company_directory(company_symbol, year, doc_type)
            file_path = target_dir / clean_filename
            
            # Check if file already exists
            if file_path.exists():
                logger.warning(f"File already exists: {file_path}")
                # You might want to handle versioning here
                file_path = self._get_unique_filename(file_path)
            
            # Validate file size
            if not validate_file_size(len(content)):
                return False, None, None
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Validate saved file
            if not validate_file_type(str(file_path)):
                logger.warning(f"File type validation failed: {file_path}")
                # Don't delete, but log the issue
            
            # Get file information
            file_info = self.get_file_info(file_path)
            
            logger.info(f"Document saved: {file_path} ({format_file_size(len(content))})")
            
            return True, str(file_path), file_info
            
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            return False, None, None
    
    def get_file_info(self, file_path: Path) -> Dict:
        """Get comprehensive file information"""
        try:
            stat = file_path.stat()
            
            # Calculate file hash
            file_hash = self.calculate_file_hash(file_path)
            
            # Basic file info
            file_info = {
                'file_path': str(file_path),
                'filename': file_path.name,
                'file_size': stat.st_size,
                'file_hash': file_hash,
                'file_extension': file_path.suffix.lower(),
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'modified_at': datetime.fromtimestamp(stat.st_mtime),
                'is_readable': True,
                'validation_errors': []
            }
            
            # Validate content
            is_valid, error_msg = validate_document_content(str(file_path))
            file_info['is_valid'] = is_valid
            if error_msg:
                file_info['validation_errors'].append(error_msg)
            
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return {
                'file_path': str(file_path),
                'filename': file_path.name,
                'is_readable': False,
                'validation_errors': [str(e)]
            }
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def _get_unique_filename(self, file_path: Path) -> Path:
        """Generate unique filename if file already exists"""
        base_name = file_path.stem
        extension = file_path.suffix
        parent_dir = file_path.parent
        counter = 1
        
        while True:
            new_filename = f"{base_name}_{counter}{extension}"
            new_path = parent_dir / new_filename
            if not new_path.exists():
                return new_path
            counter += 1
            
            # Prevent infinite loop
            if counter > 1000:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"{base_name}_{timestamp}{extension}"
                return parent_dir / new_filename
    
    def delete_document(self, file_path: str) -> bool:
        """Delete a document file"""
        try:
            file_path = Path(file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Document deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete document {file_path}: {e}")
            return False
    
    def move_document(self, old_path: str, new_path: str) -> bool:
        """Move document to new location"""
        try:
            old_path = Path(old_path)
            new_path = Path(new_path)
            
            # Ensure target directory exists
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(old_path), str(new_path))
            logger.info(f"Document moved: {old_path} -> {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move document {old_path} -> {new_path}: {e}")
            return False
    
    def get_company_stats(self, company_symbol: str) -> Dict:
        """Get storage statistics for a company"""
        try:
            company_base_dir = self.base_dir / company_symbol
            
            if not company_base_dir.exists():
                return {
                    'company_symbol': company_symbol,
                    'total_files': 0,
                    'total_size': 0,
                    'document_types': {},
                    'years': {}
                }
            
            stats = {
                'company_symbol': company_symbol,
                'total_files': 0,
                'total_size': 0,
                'document_types': {},
                'years': {}
            }
            
            # Walk through company directory
            for year_dir in company_base_dir.iterdir():
                if not year_dir.is_dir():
                    continue
                
                year = year_dir.name
                stats['years'][year] = {
                    'files': 0,
                    'size': 0,
                    'document_types': {}
                }
                
                for doc_type_dir in year_dir.iterdir():
                    if not doc_type_dir.is_dir():
                        continue
                    
                    doc_type = doc_type_dir.name
                    type_files = 0
                    type_size = 0
                    
                    for file_path in doc_type_dir.iterdir():
                        if file_path.is_file():
                            file_size = file_path.stat().st_size
                            type_files += 1
                            type_size += file_size
                    
                    # Update stats
                    stats['total_files'] += type_files
                    stats['total_size'] += type_size
                    
                    stats['years'][year]['files'] += type_files
                    stats['years'][year]['size'] += type_size
                    stats['years'][year]['document_types'][doc_type] = {
                        'files': type_files,
                        'size': type_size
                    }
                    
                    if doc_type not in stats['document_types']:
                        stats['document_types'][doc_type] = {
                            'files': 0,
                            'size': 0
                        }
                    
                    stats['document_types'][doc_type]['files'] += type_files
                    stats['document_types'][doc_type]['size'] += type_size
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get company stats for {company_symbol}: {e}")
            return {
                'company_symbol': company_symbol,
                'total_files': 0,
                'total_size': 0,
                'error': str(e)
            }
    
    def cleanup_empty_directories(self, company_symbol: Optional[str] = None) -> int:
        """Clean up empty directories"""
        cleaned_count = 0
        
        try:
            if company_symbol:
                # Clean specific company directory
                company_dir = self.base_dir / company_symbol
                if company_dir.exists():
                    cleaned_count = self._cleanup_directory_tree(company_dir)
            else:
                # Clean all company directories
                for company_dir in self.base_dir.iterdir():
                    if company_dir.is_dir():
                        cleaned_count += self._cleanup_directory_tree(company_dir)
            
            logger.info(f"Cleaned up {cleaned_count} empty directories")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup directories: {e}")
            return 0
    
    def _cleanup_directory_tree(self, directory: Path) -> int:
        """Recursively clean up empty directories"""
        cleaned_count = 0
        
        try:
            for item in directory.iterdir():
                if item.is_dir():
                    cleaned_count += self._cleanup_directory_tree(item)
            
            # Remove directory if it's empty
            if not any(directory.iterdir()):
                directory.rmdir()
                logger.debug(f"Removed empty directory: {directory}")
                cleaned_count += 1
            
        except Exception as e:
            logger.debug(f"Could not cleanup directory {directory}: {e}")
        
        return cleaned_count
    
    def get_storage_summary(self) -> Dict:
        """Get overall storage summary"""
        try:
            summary = {
                'total_companies': 0,
                'total_files': 0,
                'total_size': 0,
                'total_size_formatted': '',
                'companies': {},
                'document_types': {},
                'years': {}
            }
            
            if not self.base_dir.exists():
                return summary
            
            for company_dir in self.base_dir.iterdir():
                if not company_dir.is_dir():
                    continue
                
                company_symbol = company_dir.name
                company_stats = self.get_company_stats(company_symbol)
                
                if 'error' not in company_stats:
                    summary['total_companies'] += 1
                    summary['total_files'] += company_stats['total_files']
                    summary['total_size'] += company_stats['total_size']
                    summary['companies'][company_symbol] = company_stats
                    
                    # Aggregate document types
                    for doc_type, stats in company_stats['document_types'].items():
                        if doc_type not in summary['document_types']:
                            summary['document_types'][doc_type] = {'files': 0, 'size': 0}
                        summary['document_types'][doc_type]['files'] += stats['files']
                        summary['document_types'][doc_type]['size'] += stats['size']
                    
                    # Aggregate years
                    for year, stats in company_stats['years'].items():
                        if year not in summary['years']:
                            summary['years'][year] = {'files': 0, 'size': 0}
                        summary['years'][year]['files'] += stats['files']
                        summary['years'][year]['size'] += stats['size']
            
            summary['total_size_formatted'] = format_file_size(summary['total_size'])
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get storage summary: {e}")
            return {'error': str(e)}
    
    def validate_storage_integrity(self) -> Dict:
        """Validate storage integrity and report issues"""
        issues = {
            'missing_files': [],
            'corrupted_files': [],
            'invalid_files': [],
            'duplicate_files': {},
            'total_issues': 0
        }
        
        try:
            file_hashes = {}
            
            for root, dirs, files in os.walk(self.base_dir):
                for filename in files:
                    file_path = Path(root) / filename
                    
                    try:
                        # Check if file is readable
                        if not file_path.exists():
                            issues['missing_files'].append(str(file_path))
                            continue
                        
                        # Validate file type
                        if not validate_file_type(str(file_path)):
                            issues['invalid_files'].append(str(file_path))
                        
                        # Validate content
                        is_valid, error = validate_document_content(str(file_path))
                        if not is_valid:
                            issues['corrupted_files'].append({
                                'file': str(file_path),
                                'error': error
                            })
                        
                        # Check for duplicates
                        file_hash = self.calculate_file_hash(file_path)
                        if file_hash in file_hashes:
                            if file_hash not in issues['duplicate_files']:
                                issues['duplicate_files'][file_hash] = []
                            issues['duplicate_files'][file_hash].append(str(file_path))
                        else:
                            file_hashes[file_hash] = str(file_path)
                        
                    except Exception as e:
                        logger.error(f"Error validating file {file_path}: {e}")
                        issues['corrupted_files'].append({
                            'file': str(file_path),
                            'error': str(e)
                        })
            
            # Calculate total issues
            issues['total_issues'] = (
                len(issues['missing_files']) +
                len(issues['corrupted_files']) +
                len(issues['invalid_files']) +
                sum(len(files) - 1 for files in issues['duplicate_files'].values() if len(files) > 1)
            )
            
            logger.info(f"Storage integrity check completed: {issues['total_issues']} issues found")
            
        except Exception as e:
            logger.error(f"Failed to validate storage integrity: {e}")
            issues['error'] = str(e)
        
        return issues