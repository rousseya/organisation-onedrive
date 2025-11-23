"""
Module pour analyser les PDFs avec une IA (LLM) pour une meilleure classification
"""
import logging
import os
from typing import Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement si disponibles
load_dotenv()

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Classe pour analyser les PDFs avec une IA"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "mistral"):
        """
        Initialise l'analyseur IA
        
        Args:
            api_key: Clé API Mistral.ai
            model: Type de modèle à utiliser ('mistral', 'local', 'groq', 'ollama')
        """
        self.api_key = api_key or os.getenv('AI_API_KEY')
        self.model = model or os.getenv('AI_MODEL', 'mistral')
        self.use_ai = os.getenv('USE_AI_ANALYSIS', 'True').lower() == 'true'
        
        # Configuration basée sur le modèle
        if self.model == 'mistral' and self.api_key:
            try:
                from mistralai import Mistral
                from mistralai.models.usermessage import UserMessage
                from mistralai.models.systemmessage import SystemMessage
                
                self.client = Mistral(api_key=self.api_key)
                self.UserMessage = UserMessage
                self.SystemMessage = SystemMessage
                logger.info("✓ Analyseur Mistral.ai initialisé avec succès")
            except ImportError:
                logger.warning("mistralai non installé, installation requise: pip install mistralai")
                self.use_ai = False
            except Exception as e:
                logger.warning(f"Erreur initialisation Mistral: {e}")
                self.use_ai = False
        
        elif self.model == 'groq' and self.api_key:
            try:
                import groq
                self.groq_client = groq.Groq(api_key=self.api_key)
                logger.info("✓ Analyseur Groq initialisé")
            except ImportError:
                logger.warning("groq non installé")
                self.use_ai = False
        
        elif self.model == 'ollama':
            try:
                import requests
                self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
                logger.info("✓ Analyseur Ollama configuré")
            except Exception as e:
                logger.warning(f"Ollama non accessible: {e}")
                self.use_ai = False
        
        else:
            logger.info("Mode d'analyse heuristique")
    
    def analyze_document(self, content: str, filename: str = "") -> Tuple[str, str, float]:
        """
        Analyse un document avec IA pour obtenir une description et une catégorie
        
        Args:
            content: Texte extrait du PDF
            filename: Nom du fichier
        
        Returns:
            Tuple (catégorie, description_ia, score_confiance)
        """
        if not self.use_ai or not content:
            return "", "Pas d'analyse IA", 0.0
        
        try:
            if self.model == 'mistral':
                return self._analyze_with_mistral(content, filename)
            elif self.model == 'groq':
                return self._analyze_with_groq(content, filename)
            elif self.model == 'ollama':
                return self._analyze_with_ollama(content, filename)
            else:
                return self._analyze_with_heuristics(content, filename)
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse IA: {str(e)}")
            return "", f"Erreur analyse: {str(e)}", 0.0
    
    def _analyze_with_heuristics(self, content: str, filename: str) -> Tuple[str, str, float]:
        """
        Analyse heuristique basique (sans IA)
        """
        description = "Analyse heuristique"
        
        # Détecter le type de document par mots-clés
        content_lower = content.lower()[:500]
        
        if any(word in content_lower for word in ['vaccination', 'vaccin', 'médecin', 'santé', 'hopital', 'lucie']):
            return "Santé", "Document de vaccination détecté", 0.7
        elif any(word in content_lower for word in ['facture', 'invoice', 'paiement', 'bancaire', 'iban']):
            return "Finances", "Document financier détecté", 0.7
        elif any(word in content_lower for word in ['internet', 'fibre', 'adsl', 'télécom', 'opérateur']):
            return "Internet et Télécom", "Document télécom détecté", 0.7
        
        return "", description, 0.0
    
    def _analyze_with_mistral(self, content: str, filename: str) -> Tuple[str, str, float]:
        """
        Analyse avec Mistral.ai (nouvelle API)
        """
        try:
            # Préparer le prompt
            system_prompt = """Tu es un expert en classification de documents.

Analyse ce document et classifit-le dans l'une des catégories suivantes:
- Santé
- Finances
- Internet et Télécom
- Documents Identité
- Loisirs et Culture
- Administratif
- Études et Exercices
- Autre

Réponds EXACTEMENT avec ce format (une ligne par paramètre):
CATEGORIE: [catégorie]
DESCRIPTION: [description courte]
CONFIANCE: [0.0 à 1.0]"""
            
            user_prompt = f"""Document à analyser:
Nom: {filename}
Contenu (premiers 1500 caractères):
{content[:1500]}

Réponds maintenant avec le format exact demandé:"""
            
            # Appeler l'API Mistral (nouvelle API)
            message = self.client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            response_text = message.choices[0].message.content
            logger.debug(f"Réponse Mistral: {response_text}")
            
            # Parser la réponse
            category = ""
            description = ""
            confidence = 0.5
            
            for line in response_text.split('\n'):
                line = line.strip()
                if line.startswith('CATEGORIE:'):
                    category = line.replace('CATEGORIE:', '').strip()
                elif line.startswith('DESCRIPTION:'):
                    description = line.replace('DESCRIPTION:', '').strip()
                elif line.startswith('CONFIANCE:'):
                    try:
                        conf_str = line.replace('CONFIANCE:', '').strip()
                        confidence = float(conf_str)
                    except ValueError:
                        confidence = 0.5
            
            if category:
                logger.info(f"✓ Analyse Mistral: {category} (confiance: {confidence:.0%})")
                return category, description, confidence
        
        except Exception as e:
            logger.error(f"Erreur Mistral: {str(e)}")
        
        return "", f"Erreur Mistral: {str(e)}", 0.0
    
    def _analyze_with_groq(self, content: str, filename: str) -> Tuple[str, str, float]:
        """
        Analyse avec Groq (API gratuite rapide)
        """
        try:
            message = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": """Tu es un expert en classification de documents.
                        Analyse le document et classe-le dans une des catégories.
                        Réponds avec le format:
                        CATEGORIE: [catégorie]
                        DESCRIPTION: [description]
                        CONFIANCE: [0.0 à 1.0]"""
                    },
                    {
                        "role": "user",
                        "content": f"Analyse ce document:\n\nNom: {filename}\n\nContenu:\n{content[:2000]}"
                    }
                ],
                model="mixtral-8x7b-32768",
                temperature=0.3,
                max_tokens=200
            )
            
            response_text = message.choices[0].message.content
            
            # Parser la réponse
            category = ""
            description = ""
            confidence = 0.5
            
            for line in response_text.split('\n'):
                if 'CATEGORIE:' in line:
                    category = line.split('CATEGORIE:')[1].strip()
                elif 'DESCRIPTION:' in line:
                    description = line.split('DESCRIPTION:')[1].strip()
                elif 'CONFIANCE:' in line:
                    try:
                        confidence = float(line.split('CONFIANCE:')[1].strip())
                    except:
                        confidence = 0.5
            
            logger.info(f"✓ Analyse Groq: {category} (confiance: {confidence:.0%})")
            return category, description, confidence
        
        except Exception as e:
            logger.error(f"Erreur Groq: {str(e)}")
            return "", f"Erreur Groq: {str(e)}", 0.0
    
    def _analyze_with_ollama(self, content: str, filename: str) -> Tuple[str, str, float]:
        """
        Analyse avec Ollama (modèles locaux)
        """
        try:
            import requests
            
            prompt = f"""Tu es un expert en classification de documents.
Analyse ce document et réponds avec le format suivant:
CATEGORIE: [catégorie du document]
DESCRIPTION: [brève description]
CONFIANCE: [score de 0 à 1]

Nom du fichier: {filename}
Contenu du document:
{content[:1000]}"""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                response_text = response.json().get('response', '')
                
                # Parser la réponse
                category = ""
                description = ""
                confidence = 0.5
                
                for line in response_text.split('\n'):
                    if 'CATEGORIE:' in line:
                        category = line.split('CATEGORIE:')[1].strip()
                    elif 'DESCRIPTION:' in line:
                        description = line.split('DESCRIPTION:')[1].strip()
                    elif 'CONFIANCE:' in line:
                        try:
                            confidence = float(line.split('CONFIANCE:')[1].strip())
                        except:
                            confidence = 0.5
                
                logger.info(f"✓ Analyse Ollama: {category} (confiance: {confidence:.0%})")
                return category, description, confidence
        
        except Exception as e:
            logger.error(f"Erreur Ollama: {str(e)}")
        
        return "", f"Erreur Ollama: {str(e)}", 0.0
    
    def get_ai_insights(self, content: str, filename: str) -> dict:
        """
        Obtient des insights complets sur un document
        
        Returns:
            Dictionnaire avec catégorie, description et confiance
        """
        if not self.use_ai:
            return {
                'ai_enabled': False,
                'category': '',
                'description': 'Analyse IA désactivée',
                'confidence': 0.0
            }
        
        category, description, confidence = self.analyze_document(content, filename)
        
        return {
            'ai_enabled': True,
            'category': category,
            'description': description,
            'confidence': confidence,
            'model': self.model
        }
