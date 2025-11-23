"""
Generate markdown documentation for organized PDFs
"""
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFDocumentationGenerator:
    """Generate markdown documentation for PDF files"""

    def __init__(self, output_path: Path):
        """
        Initialize documentation generator
        
        Args:
            output_path: Base output path for documents
        """
        self.output_path = Path(output_path)

    def generate_documentation(self, pdf_data: Dict) -> bool:
        """
        Generate markdown documentation for a PDF
        
        Args:
            pdf_data: Dictionary containing:
                - 'path': Path to PDF file
                - 'category': Assigned category
                - 'filename': Original filename
                - 'renamed_filename': Renamed filename (without extension) from organizer
                - 'content': Extracted text content
                - 'confidence': Classification confidence
                - 'ai_result': AI analysis result (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            pdf_path = Path(pdf_data['path'])
            category = pdf_data.get('category', 'Autre')
            content = pdf_data.get('content', '')
            confidence = pdf_data.get('confidence', 0)
            ai_result = pdf_data.get('ai_result', {})
            
            # Calculate hashes
            md5_hash = self._calculate_md5(pdf_path)
            perceptual_hash = self._calculate_perceptual_hash(pdf_path)
            
            # Use renamed filename if available, otherwise use original
            if 'renamed_filename' in pdf_data:
                md_filename = pdf_data['renamed_filename'] + '.md'
            else:
                md_filename = pdf_path.stem + '.md'
            category_folder = self.output_path / category
            md_path = category_folder / md_filename
            
            # Create markdown content
            md_content = self._create_markdown_content(
                pdf_path.name,
                category,
                confidence,
                content,
                ai_result,
                str(pdf_path),
                md5_hash,
                perceptual_hash
            )
            
            # Write markdown file
            md_path.parent.mkdir(parents=True, exist_ok=True)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"Documentation created: {md_path.name}")
            return True
        
        except Exception as e:
            logger.error(f"Error generating documentation: {e}")
            return False

    def _create_markdown_content(self, filename: str, category: str, 
                                 confidence: float, content: str, 
                                 ai_result: Dict, source_path: str = '',
                                 md5_hash: str = '', perceptual_hash: str = '') -> str:
        """
        Create markdown content for a PDF
        
        Args:
            filename: PDF filename
            category: Document category
            confidence: Classification confidence (0-100)
            content: Extracted text
            ai_result: AI analysis results
            source_path: Original source path of the PDF
            md5_hash: MD5 hash of the PDF file
            perceptual_hash: Perceptual hash of the PDF file
        
        Returns:
            Markdown content as string
        """
        # Extract AI information
        document_type = ai_result.get('document_type', 'Unknown')
        source = ai_result.get('source', 'keyword_analysis')
        reason = ai_result.get('reason', 'Classification based on content')
        key_info = ai_result.get('details', {}).get('key_info', '')
        language = ai_result.get('details', {}).get('language', 'Unknown')
        
        # Build markdown
        md = []
        
        # Header
        md.append(f"# {filename}")
        md.append("")
        
        # Metadata
        md.append("## Document Information")
        md.append("")
        md.append(f"| Field | Value |")
        md.append(f"|-------|-------|")
        md.append(f"| **Category** | {category} |")
        md.append(f"| **Type** | {document_type} |")
        md.append(f"| **Confidence** | {confidence:.0f}% |")
        md.append(f"| **Analysis Source** | {source} |")
        md.append(f"| **Language** | {language} |")
        md.append(f"| **Generated** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |")
        md.append("")
        
        # Source Information
        if source_path:
            md.append("## Source")
            md.append("")
            md.append(f"**Original Location:**")
            md.append("")
            md.append(f"- {source_path}")
            md.append("")
        
        # Hash Information
        if md5_hash or perceptual_hash:
            md.append("## Integrity & Deduplication")
            md.append("")
            md.append(f"| Hash Type | Value |")
            md.append(f"|-----------|-------|")
            if md5_hash:
                md.append(f"| **MD5** | `{md5_hash}` |")
            if perceptual_hash:
                md.append(f"| **Perceptual Hash** | `{perceptual_hash}` |")
            md.append("")
            md.append("*Use MD5 for exact duplicate detection or Perceptual Hash to find similar documents.*")
            md.append("")
        
        # Analysis
        md.append("## Analysis")
        md.append("")
        md.append(f"**Reason:** {reason}")
        md.append("")
        
        if key_info:
            md.append("**Key Information:**")
            md.append("")
            md.append(f"{key_info}")
            md.append("")
        
        # Transcription/Content
        if content:
            md.append("## Content / Transcription")
            md.append("")
            
            # Truncate very long content
            if len(content) > 5000:
                md.append(f"{content[:5000]}")
                md.append("")
                md.append(f"*(Content truncated - {len(content)} total characters)*")
            else:
                md.append(content)
            md.append("")
        else:
            md.append("## Content / Transcription")
            md.append("")
            md.append("*No text content extracted (image-based or scanned document)*")
            md.append("")
        
        # Footer
        md.append("---")
        md.append("")
        md.append("*This documentation was automatically generated by PDF Analyzer.*")
        
        return "\n".join(md)

    def generate_batch_documentation(self, pdf_data_list: list) -> Dict:
        """
        Generate documentation for multiple PDFs
        
        Args:
            pdf_data_list: List of PDF data dictionaries
        
        Returns:
            Statistics dictionary
        """
        stats = {
            'total': len(pdf_data_list),
            'success': 0,
            'failed': 0,
            'by_category': {}
        }
        
        logger.info(f"Generating documentation for {len(pdf_data_list)} PDFs...")
        
        for pdf_data in pdf_data_list:
            category = pdf_data.get('category', 'Autre')
            
            if self.generate_documentation(pdf_data):
                stats['success'] += 1
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            else:
                stats['failed'] += 1
        
        return stats

    def _calculate_md5(self, file_path: Path) -> str:
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
            return "N/A"

    def _calculate_perceptual_hash(self, file_path: Path) -> str:
        """
        Calculate Perceptual Hash of a PDF using page fingerprinting
        
        Args:
            file_path: Path to the PDF file
        
        Returns:
            Perceptual hash as hexadecimal string (based on first page dimensions and content)
        """
        try:
            import pdfplumber
            
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) == 0:
                    return "N/A"
                
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
            logger.error(f"Error calculating perceptual hash for {file_path}: {e}")
            return "N/A"
