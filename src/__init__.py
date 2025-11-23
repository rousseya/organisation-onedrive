"""
Package principal pour l'organisation des PDFs
"""
from .pdf_extractor import PDFExtractor
from .pdf_classifier import PDFClassifier
from .pdf_organizer import PDFOrganizer

__version__ = "1.0.0"
__all__ = ["PDFExtractor", "PDFClassifier", "PDFOrganizer"]
