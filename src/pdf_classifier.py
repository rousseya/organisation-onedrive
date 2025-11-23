"""
Module pour classifier les fichiers PDF par catégorie
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Tuple
import re

logger = logging.getLogger(__name__)


class PDFClassifier:
    """Classe pour classifier les PDFs en fonction de leur contenu"""
    
    def __init__(self, config_path: str, use_ai: bool = None):
        """
        Initialise le classificateur avec les catégories
        
        Args:
            config_path: Chemin vers le fichier de configuration des catégories
            use_ai: Utiliser l'analyse IA (None = déterminé par .env)
        """
        self.categories = self._load_categories(config_path)
        
        # Déterminer si on doit utiliser l'IA
        if use_ai is None:
            use_ai = os.getenv('USE_AI_ANALYSIS', 'True').lower() == 'true'
        
        self.use_ai = use_ai
        
        # Initialiser l'analyseur IA si activé
        if self.use_ai:
            try:
                from src.pdf_ai_analyzer_v2 import AIAnalyzer
                self.ai_analyzer = AIAnalyzer()
                logger.info("[OK] AI analyzer initialized (with Vision support)")
            except Exception as e:
                logger.warning(f"Unable to initialize AI analyzer: {e}")
                self.use_ai = False
                self.ai_analyzer = None
        else:
            self.ai_analyzer = None
    
    def _load_categories(self, config_path: str) -> Dict:
        """Charge les catégories depuis le fichier de configuration"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('categories', {})
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
            return {}
    
    def classify(self, pdf_path: str, filename: str, content: str) -> Tuple[str, float]:
        """
        Classifie un document en fonction de son chemin, nom et contenu
        
        Args:
            pdf_path: Chemin complet du fichier PDF
            filename: Nom du fichier
            content: Contenu textuel du document
        
        Returns:
            Tuple (catégorie, score de confiance)
        """
        result = self.classify_with_details(pdf_path, filename, content)
        return result['category'], result['confidence'] / 100
    
    def classify_with_details(self, pdf_path: str, filename: str, content: str) -> Dict:
        """
        Classifie un document et retourne les détails complets
        
        Args:
            pdf_path: Chemin complet du fichier PDF
            filename: Nom du fichier
            content: Contenu textuel du document
        
        Returns:
            Dictionnaire avec category, confidence, et ai_result
        """
        # Essayer d'abord avec l'IA si disponible
        if self.use_ai and self.ai_analyzer:
            try:
                result = self.ai_analyzer.analyze_document(pdf_path, content)
                
                if result['category'] and result['confidence'] >= 50:
                    logger.info(f"Classification IA: {result['category']} (confiance: {result['confidence']:.0f}%, source: {result['source']})")
                    return {
                        'category': result['category'],
                        'confidence': result['confidence'],
                        'ai_result': result
                    }
            except Exception as e:
                logger.debug(f"Erreur classification IA: {e}")
        
        # Retomber sur la classification basée sur les keywords
        category, confidence = self._classify_by_keywords(filename, content)
        
        return {
            'category': category,
            'confidence': confidence * 100,
            'ai_result': {
                'category': category,
                'confidence': confidence * 100,
                'document_type': 'Unknown',
                'source': 'keyword_analysis',
                'reason': f'Classification based on keywords',
                'details': {}
            }
        }
    
    def _classify_by_keywords(self, filename: str, content: str) -> Tuple[str, float]:
        """Classification basée sur les mots-clés (ancienne méthode)"""
        full_text = f"{filename} {content}".lower()
        scores = {}
        
        # Analyser chaque catégorie
        for category_name, category_info in self.categories.items():
            keywords = category_info.get('keywords', [])
            
            if not keywords:  # "Autre" n'a pas de keywords
                scores[category_name] = 0
                continue
            
            # Calculer le score pour cette catégorie
            score = self._calculate_score(full_text, keywords)
            scores[category_name] = score
        
        # Trouver la catégorie avec le score le plus élevé
        if not scores or all(v == 0 for v in scores.values()):
            return "Autre", 0.0
        
        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]
        
        return best_category, confidence
    
    def _calculate_score(self, text: str, keywords: list) -> float:
        """
        Calcule le score de correspondance entre le texte et les keywords
        
        Args:
            text: Texte à analyser
            keywords: Liste des keywords
        
        Returns:
            Score de correspondance (0-1)
        """
        if not keywords:
            return 0.0
        
        matches = 0
        for keyword in keywords:
            # Chercher le keyword en tant que mot entier
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, text):
                matches += 1
        
        return matches / len(keywords)
    
    def get_category_folder(self, category_name: str) -> str:
        """Retourne le nom du dossier pour une catégorie"""
        return self.categories.get(category_name, {}).get('folder', 'Autre')
