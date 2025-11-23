"""
Module pour extraire le texte des fichiers PDF
"""
import pdfplumber
import logging
import hashlib
import io
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Classe pour extraire le texte des fichiers PDF"""
    
    def __init__(self):
        self.supported_extensions = ['.pdf']
    
    def extract_text(self, pdf_path: Path, max_pages: int = 2) -> str:
        """
        Extrait le texte d'un fichier PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            max_pages: Nombre maximum de pages à analyser
        
        Returns:
            Texte extrait du PDF
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                # Limiter à max_pages pour améliorer la performance
                pages_to_process = min(len(pdf.pages), max_pages)
                for i in range(pages_to_process):
                    page = pdf.pages[i]
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            
            logger.info(f"Texte extrait avec succès de {pdf_path.name}")
            return text.lower()
        
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du texte de {pdf_path}: {str(e)}")
            return ""
    
    def extract_metadata(self, pdf_path: Path) -> dict:
        """
        Extrait les métadonnées d'un fichier PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
        
        Returns:
            Dictionnaire contenant les métadonnées
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                metadata = pdf.metadata or {}
                return {
                    'title': metadata.get('Title', ''),
                    'subject': metadata.get('Subject', ''),
                    'author': metadata.get('Author', ''),
                    'pages': len(pdf.pages)
                }
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des métadonnées de {pdf_path}: {str(e)}")
            return {}
    
    def calculate_md5(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of a file
        
        Args:
            file_path: Path to the file
        
        Returns:
            MD5 hash as hexadecimal string
        """
        try:
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating MD5 for {file_path}: {e}")
            return ""
    
    def calculate_perceptual_hash(self, pdf_path: Path) -> str:
        """
        Calculate Perceptual Hash of a PDF using page fingerprinting
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            Perceptual hash as hexadecimal string (based on first page dimensions and content)
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return ""
                
                # Use first page properties for perceptual hashing
                first_page = pdf.pages[0]
                
                # Create a fingerprint from page dimensions and text content hash
                page_height = first_page.height
                page_width = first_page.width
                
                # Extract first 1000 characters to create a content-based hash
                page_text = first_page.extract_text()[:1000] if first_page.extract_text() else ""
                
                # Combine page properties and content for perceptual hash
                fingerprint_data = f"{page_width}_{page_height}_{len(page_text)}_{page_text}".encode('utf-8')
                phash = hashlib.sha256(fingerprint_data).hexdigest()[:16]  # Take first 16 chars
                
                return phash
        except Exception as e:
            logger.error(f"Error calculating perceptual hash for {pdf_path}: {e}")
            return ""
