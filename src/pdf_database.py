"""
SQLite database management for tracking processed PDFs
"""
import sqlite3
import logging
import hashlib
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFDatabase:
    """Manage SQLite database for PDF tracking and deduplication"""
    
    def __init__(self, db_path: Path):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database schema if it doesn't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create PDFs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS pdfs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        md5_hash TEXT UNIQUE NOT NULL,
                        perceptual_hash TEXT,
                        original_filename TEXT NOT NULL,
                        category TEXT NOT NULL,
                        organized_filename TEXT NOT NULL,
                        organized_path TEXT NOT NULL,
                        source_paths TEXT NOT NULL,
                        confidence REAL,
                        document_type TEXT,
                        processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index on md5_hash for faster lookups
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_md5_hash ON pdfs(md5_hash)
                ''')
                
                # Create index on perceptual_hash for similarity searches
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_perceptual_hash ON pdfs(perceptual_hash)
                ''')
                
                conn.commit()
                logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def pdf_exists(self, md5_hash: str) -> bool:
        """
        Check if PDF with given MD5 hash already exists
        
        Args:
            md5_hash: MD5 hash of the PDF
        
        Returns:
            True if exists, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM pdfs WHERE md5_hash = ?', (md5_hash,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking PDF existence: {e}")
            return False
    
    def get_pdf_record(self, md5_hash: str) -> Optional[Dict]:
        """
        Retrieve PDF record by MD5 hash
        
        Args:
            md5_hash: MD5 hash of the PDF
        
        Returns:
            Dictionary with PDF data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM pdfs WHERE md5_hash = ?', (md5_hash,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error retrieving PDF record: {e}")
            return None
    
    def add_pdf_record(self, pdf_data: Dict) -> bool:
        """
        Add or update PDF record in database
        
        Args:
            pdf_data: Dictionary containing:
                - md5_hash: MD5 hash
                - perceptual_hash: Perceptual hash
                - original_filename: Original filename
                - category: Document category
                - organized_filename: Renamed filename
                - organized_path: Full path to organized PDF
                - source_path: Original source path
                - confidence: Classification confidence
                - document_type: Type of document
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare source paths as JSON string (to allow multiple sources)
            source_paths = pdf_data.get('source_paths', [])
            if isinstance(source_paths, str):
                source_paths = [source_paths]
            import json
            source_paths_json = json.dumps(source_paths)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Try to update first
                cursor.execute('''
                    UPDATE pdfs 
                    SET perceptual_hash = ?, 
                        original_filename = ?,
                        category = ?,
                        organized_filename = ?,
                        organized_path = ?,
                        source_paths = ?,
                        confidence = ?,
                        document_type = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE md5_hash = ?
                ''', (
                    pdf_data.get('perceptual_hash'),
                    pdf_data.get('original_filename'),
                    pdf_data.get('category'),
                    pdf_data.get('organized_filename'),
                    pdf_data.get('organized_path'),
                    source_paths_json,
                    pdf_data.get('confidence'),
                    pdf_data.get('document_type'),
                    pdf_data.get('md5_hash')
                ))
                
                # If no rows were updated, insert new record
                if cursor.rowcount == 0:
                    cursor.execute('''
                        INSERT INTO pdfs (
                            md5_hash, perceptual_hash, original_filename,
                            category, organized_filename, organized_path,
                            source_paths, confidence, document_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        pdf_data.get('md5_hash'),
                        pdf_data.get('perceptual_hash'),
                        pdf_data.get('original_filename'),
                        pdf_data.get('category'),
                        pdf_data.get('organized_filename'),
                        pdf_data.get('organized_path'),
                        source_paths_json,
                        pdf_data.get('confidence'),
                        pdf_data.get('document_type')
                    ))
                
                conn.commit()
                logger.info(f"PDF record saved: {pdf_data.get('md5_hash')[:8]}...")
                return True
        except Exception as e:
            logger.error(f"Error saving PDF record: {e}")
            return False
    
    def update_source_path(self, md5_hash: str, new_source_path: str) -> bool:
        """
        Update source path for an existing PDF (add to list of sources)
        
        Args:
            md5_hash: MD5 hash of the PDF
            new_source_path: New source path to add
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get existing source paths
                cursor.execute('SELECT source_paths FROM pdfs WHERE md5_hash = ?', (md5_hash,))
                row = cursor.fetchone()
                
                if row:
                    source_paths = json.loads(row[0])
                    if new_source_path not in source_paths:
                        source_paths.append(new_source_path)
                        
                        cursor.execute('''
                            UPDATE pdfs 
                            SET source_paths = ?,
                                last_updated = CURRENT_TIMESTAMP
                            WHERE md5_hash = ?
                        ''', (json.dumps(source_paths), md5_hash))
                        
                        conn.commit()
                        logger.info(f"Source path updated for {md5_hash[:8]}...")
                        return True
        except Exception as e:
            logger.error(f"Error updating source path: {e}")
        
        return False
    
    def find_similar_pdfs(self, perceptual_hash: str, threshold: int = 4) -> List[Dict]:
        """
        Find similar PDFs using perceptual hash (Hamming distance)
        
        Args:
            perceptual_hash: Perceptual hash to search for
            threshold: Maximum Hamming distance (0-16 for 16-char hex hash)
        
        Returns:
            List of similar PDF records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get all PDFs and calculate Hamming distance
                cursor.execute('SELECT * FROM pdfs WHERE perceptual_hash IS NOT NULL')
                rows = cursor.fetchall()
                
                similar = []
                for row in rows:
                    distance = self._hamming_distance(perceptual_hash, row['perceptual_hash'])
                    if distance <= threshold:
                        record = dict(row)
                        record['similarity_distance'] = distance
                        similar.append(record)
                
                return sorted(similar, key=lambda x: x['similarity_distance'])
        except Exception as e:
            logger.error(f"Error finding similar PDFs: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """
        Get database statistics
        
        Returns:
            Dictionary with statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM pdfs')
                total_pdfs = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT category, COUNT(*) as count 
                    FROM pdfs 
                    GROUP BY category 
                    ORDER BY count DESC
                ''')
                by_category = {row[0]: row[1] for row in cursor.fetchall()}
                
                cursor.execute('''
                    SELECT COUNT(DISTINCT md5_hash) FROM pdfs
                ''')
                unique_pdfs = cursor.fetchone()[0]
                
                return {
                    'total_records': total_pdfs,
                    'unique_pdfs': unique_pdfs,
                    'by_category': by_category,
                    'db_size': self.db_path.stat().st_size if self.db_path.exists() else 0
                }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    @staticmethod
    def _hamming_distance(hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance between two hex strings
        
        Args:
            hash1: First hex string
            hash2: Second hex string
        
        Returns:
            Hamming distance
        """
        if len(hash1) != len(hash2):
            return float('inf')
        
        try:
            val1 = int(hash1, 16)
            val2 = int(hash2, 16)
            xor = val1 ^ val2
            return bin(xor).count('1')
        except ValueError:
            return float('inf')

