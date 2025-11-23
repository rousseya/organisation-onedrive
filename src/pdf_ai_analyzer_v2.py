"""
AI-powered PDF analyzer using Mistral API (v2 with Vision support)
"""
import os
import json
import re
import base64
import logging
import io
from pathlib import Path
from typing import Optional, Tuple, Dict
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Analyze PDF content using Mistral AI with Vision API support for scanned documents"""

    def __init__(self, api_key: Optional[str] = None, model: str = "mistral"):
        """
        Initialize AI analyzer with Mistral API
        
        Args:
            api_key: API key for Mistral
            model: Model type ('mistral')
        """
        self.api_key = api_key or os.getenv('AI_API_KEY')
        self.model_type = model or os.getenv('AI_MODEL', 'mistral')
        self.use_ai = os.getenv('USE_AI_ANALYSIS', 'True').lower() == 'true'
        
        self.text_model = 'mistral-medium'
        self.vision_model = 'pixtral-12b-2409'
        
        if self.model_type == 'mistral' and self.api_key:
            try:
                from mistralai import Mistral
                self.client = Mistral(api_key=self.api_key)
                logger.info("[OK] Mistral AI analyzer initialized")
            except ImportError:
                logger.warning("mistralai not installed")
                self.use_ai = False
            except Exception as e:
                logger.warning(f"Mistral initialization error: {e}")
                self.use_ai = False
        else:
            logger.info("AI analysis disabled")
            self.use_ai = False

    def analyze_document(self, pdf_path: str, extracted_text: str = "") -> Dict:
        """
        Analyze PDF document using text or vision
        
        Args:
            pdf_path: Path to PDF file
            extracted_text: Text extracted from PDF
        
        Returns:
            {
                'category': str,
                'confidence': float (0-100),
                'reason': str,
                'document_type': str,
                'details': dict,
                'source': 'text_analysis' | 'vision_analysis' | 'error'
            }
        """
        if not self.use_ai:
            return self._create_result('Autre', 0, 'AI analysis disabled', 'Unknown', {}, 'disabled')
        
        # If we have meaningful text, analyze it
        if extracted_text and len(extracted_text.strip()) >= 50:
            return self._analyze_with_text(extracted_text)
        
        # Otherwise try vision analysis for scanned documents
        logger.debug(f"Using vision analysis for: {Path(pdf_path).name}")
        return self._analyze_with_vision(pdf_path)

    def _analyze_with_text(self, text: str) -> Dict:
        """Analyze using text extraction with Mistral chat API"""
        try:
            prompt = f"""Analyze this document text and categorize it. Respond with JSON ONLY (no markdown, no extra text):
{{
  "category": "one of: Santé, Finances, Administratif, Internet et Télécom, Documents Identité, Loisirs et Culture, Études et Exercices, Autre",
  "confidence": 0-100,
  "document_type": "specific document type",
  "reason": "brief explanation"
}}

Document text:
{text[:2000]}"""

            response = self.client.chat.complete(
                model=self.text_model,
                messages=[{'role': 'user', 'content': prompt}],
            )
            
            response_text = response.choices[0].message.content
            logger.debug(f"Mistral response: {response_text[:200]}")
            
            # Parse JSON (handle various formats)
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                return self._create_result(
                    result.get('category', 'Autre'),
                    result.get('confidence', 50),
                    result.get('reason', 'AI text analysis'),
                    result.get('document_type', 'Unknown'),
                    result,
                    'text_analysis'
                )
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in text analysis: {e}")
        except Exception as e:
            logger.error(f"Text analysis error: {e}")
        
        return self._create_result('Autre', 0, 'Text analysis failed', 'Unknown', {}, 'error')

    def _analyze_with_vision(self, pdf_path: str) -> Dict:
        """
        Analyze scanned PDF using Mistral Vision API
        Converts first page to image and analyzes it
        """
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not available for vision analysis")
            return self._create_result('Autre', 0, 'pdfplumber not installed', 'Scanned Document', {}, 'error')
        
        try:
            logger.debug(f"Converting PDF to image: {Path(pdf_path).name}")
            
            # Render first page to image
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return self._create_result('Autre', 0, 'PDF has no pages', 'Invalid PDF', {}, 'error')
                
                page = pdf.pages[0]
                page_img = page.to_image(resolution=150)
            
            # Encode image to base64
            img_bytes = io.BytesIO()
            page_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            image_data = base64.standard_b64encode(img_bytes.read()).decode('utf-8')
            
            logger.debug(f"Sending to Mistral Vision API...")
            
            # Call Mistral Vision API
            response = self.client.chat.complete(
                model=self.vision_model,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image_url',
                                'image_url': f'data:image/png;base64,{image_data}',
                            },
                            {
                                'type': 'text',
                                'text': '''Analyze this scanned document image. Respond with JSON ONLY (no markdown):
{
  "category": "one of: Santé, Finances, Administratif, Internet et Télécom, Documents Identité, Loisirs et Culture, Études et Exercices, Autre",
  "confidence": 0-100,
  "document_type": "what type of document is this",
  "key_info": "brief summary of main content",
  "language": "detected language",
  "reason": "brief explanation"
}'''
                            }
                        ],
                    }
                ],
            )
            
            response_text = response.choices[0].message.content
            logger.debug(f"Vision response: {response_text[:200]}")
            
            # Parse JSON (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*```', response_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            
            if json_match:
                json_text = json_match.group(1) if '```' in response_text else json_match.group(0)
                result = json.loads(json_text)
                
                return self._create_result(
                    result.get('category', 'Autre'),
                    result.get('confidence', 75),
                    result.get('reason', 'Vision analysis'),
                    result.get('document_type', 'Scanned Document'),
                    result,
                    'vision_analysis'
                )
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in vision analysis: {e}")
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            import traceback
            traceback.print_exc()
        
        return self._create_result('Autre', 0, 'Vision analysis failed', 'Scanned Document', {}, 'error')

    def _create_result(self, category: str, confidence: float, reason: str, 
                      document_type: str, details: Dict, source: str) -> Dict:
        """Create standardized result dictionary"""
        return {
            'category': category,
            'confidence': min(100, max(0, confidence)),  # Clamp to 0-100
            'reason': reason,
            'document_type': document_type,
            'details': details,
            'source': source
        }

    def get_ai_insights(self, pdf_path: str, content: str) -> Dict:
        """Get complete AI insights about a document"""
        if not self.use_ai:
            return {
                'ai_enabled': False,
                'category': '',
                'description': 'AI analysis disabled',
                'confidence': 0.0,
                'model': self.model_type
            }
        
        result = self.analyze_document(pdf_path, content)
        
        return {
            'ai_enabled': True,
            'category': result['category'],
            'description': result['document_type'],
            'confidence': result['confidence'] / 100,  # Convert to 0-1 scale
            'model': self.model_type,
            'source': result['source'],
            'details': result.get('details', {})
        }
