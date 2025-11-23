"""
Module pour renommer les fichiers PDFs de manière significative
"""
import re
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class PDFRenamer:
    """Classe pour renommer les fichiers PDFs"""
    
    # Mappings pour remplacer les caractères accentués par leurs équivalents ASCII
    ACCENT_MAP = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A',
        'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
        'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
        'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N',
        '·': '_', '–': '-', '—': '-', ''': "'", ''': "'", '"': '"', '"': '"',
    }
    
    MAX_NAME_LENGTH = 26  # Nombre de caractères pour le nom (sans l'extension .pdf qui fait 4 chars)
    
    def __init__(self):
        """Initialise le renommeur"""
        pass
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Nettoie un nom de fichier pour le rendre ASCII-only, sans espaces
        
        Args:
            filename: Nom du fichier (sans extension)
        
        Returns:
            Nom nettoyé et limité à MAX_NAME_LENGTH caractères
        """
        # Remplacer les accents et caractères spéciaux
        cleaned = filename
        for accent_char, ascii_char in self.ACCENT_MAP.items():
            cleaned = cleaned.replace(accent_char, ascii_char)
        
        # Remplacer les espaces par des underscores
        cleaned = re.sub(r'\s+', '_', cleaned)
        
        # Garder seulement les caractères alphanumériques, underscores et tirets
        cleaned = re.sub(r'[^a-zA-Z0-9_-]', '', cleaned)
        
        # Supprimer les underscores/tirets multiples
        cleaned = re.sub(r'(_-|-_|__|--)+', '_', cleaned)
        
        # Supprimer les underscores/tirets au début et à la fin
        cleaned = cleaned.strip('_-')
        
        # Limiter à MAX_NAME_LENGTH caractères
        if len(cleaned) > self.MAX_NAME_LENGTH:
            cleaned = cleaned[:self.MAX_NAME_LENGTH]
        
        # S'assurer que le nom n'est pas vide
        if not cleaned:
            cleaned = "document"
        
        return cleaned
    
    def generate_name_from_content(self, filename: str, content: str, category_hint: str = None) -> str:
        """
        Génère un nom significatif basé sur le contenu du PDF
        
        Args:
            filename: Nom original du fichier
            content: Texte extrait du PDF
            category_hint: Catégorie du document (ex: 'Santé', 'Finances') pour améliorer le renommage
        
        Returns:
            Nom généré et nettoyé
        """
        words = []
        
        # Extraire des éléments du nom original
        name_without_ext = Path(filename).stem
        name_parts = re.split(r'[\s_-]+', name_without_ext)
        
        # Prendre les mots significatifs du nom original (> 3 caractères)
        # Mais EXCLURE les années/dates seules
        for part in name_parts:
            # Ignorer les parties qui sont seulement des nombres (années, dates)
            if len(part) > 3 and not part.isdigit():
                words.append(part)
        
        # Si pas assez de mots du nom, extraire du contenu
        if len(words) < 2 and content and len(content) > 10:
            # Extraire les premiers mots significatifs du contenu
            content_words = re.findall(r'\b[a-zA-Z]{4,}\b', content[:300].lower())
            
            # Ajouter jusqu'à 2 mots du contenu
            for word in content_words:
                if word not in words and len(word) > 3:
                    words.append(word)
                if len(words) >= 3:
                    break
        
        # Si aucun mot n'a été trouvé ou seulement des chiffres, utiliser le category_hint
        if not words:
            if category_hint and category_hint.lower() != 'autre':
                # Utiliser un mot-clé basé sur la catégorie
                category_keywords = {
                    'santé': 'vaccination',
                    'finances': 'document',
                    'administratif': 'admin',
                    'internet et télécom': 'telecom',
                    'documents identité': 'identité',
                    'loisirs et culture': 'activité',
                    'études et exercices': 'exercice'
                }
                keyword = category_keywords.get(category_hint.lower(), 'document')
                words.append(keyword)
                
                # Ajouter la date du fichier si disponible
                date_pattern = r'\d{4}|\d{1,2}[_-]\d{1,2}'
                dates = re.findall(date_pattern, name_without_ext)
                if dates:
                    words.append(dates[0])
            else:
                # Essayer d'extraire une date du nom du fichier
                date_pattern = r'\d{4}|\d{1,2}[_-]\d{1,2}|\d{1,2}[_-]\w{3}'
                dates = re.findall(date_pattern, name_without_ext)
                
                if dates:
                    # Utiliser la première date trouvée
                    words.append(dates[0])
                else:
                    # Fallback ultime
                    words.append("document")
        
        # Joindre les mots (max 3)
        generated_name = '_'.join(words[:3])
        
        # Nettoyer
        generated_name = self.sanitize_filename(generated_name)
        
        return generated_name
    
    def rename_file(self, source_path: Path, new_name: str = None, 
                   content: str = None, filename_hint: str = None) -> Tuple[bool, str]:
        """
        Renomme un fichier PDF
        
        Args:
            source_path: Chemin du fichier source
            new_name: Nouveau nom (sans extension). Si None, généré à partir du contenu
            content: Contenu du PDF (utilisé pour générer le nom si new_name est None)
            filename_hint: Indice pour la génération (ex: nom original)
        
        Returns:
            Tuple (succès, nouveau_chemin)
        """
        try:
            # Générer le nom s'il n'est pas fourni
            if new_name is None:
                if content is None:
                    content = ""
                hint = filename_hint or source_path.stem
                new_name = self.generate_name_from_content(hint, content)
            else:
                new_name = self.sanitize_filename(new_name)
            
            # Créer le nouveau chemin
            new_path = source_path.parent / f"{new_name}.pdf"
            
            # Si le fichier existe déjà, ajouter un suffixe numérique
            if new_path.exists():
                counter = 1
                while True:
                    suffix_name = f"{new_name}_{counter}"
                    if len(suffix_name) > self.MAX_NAME_LENGTH:
                        # Réduire le nom original si nécessaire
                        base_len = self.MAX_NAME_LENGTH - len(f"_{counter}")
                        suffix_name = f"{new_name[:base_len]}_{counter}"
                    
                    new_path = source_path.parent / f"{suffix_name}.pdf"
                    if not new_path.exists():
                        new_name = suffix_name
                        break
                    counter += 1
            
            # Renommer le fichier
            source_path.rename(new_path)
            logger.info(f"Fichier renommé: {source_path.name} -> {new_path.name}")
            
            return True, str(new_path)
        
        except Exception as e:
            logger.error(f"Erreur lors du renommage de {source_path}: {str(e)}")
            return False, str(source_path)
    
    def batch_rename_pdfs(self, folder_path: Path, content_map: dict = None) -> dict:
        """
        Renomme tous les PDFs d'un dossier
        
        Args:
            folder_path: Dossier contenant les PDFs
            content_map: Dictionnaire {nom_fichier: contenu_du_pdf}
        
        Returns:
            Dictionnaire des statistiques de renommage
        """
        if content_map is None:
            content_map = {}
        
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'renames': {}
        }
        
        pdf_files = list(folder_path.glob('*.pdf'))
        
        for pdf_file in pdf_files:
            stats['total'] += 1
            
            # Récupérer le contenu s'il existe
            content = content_map.get(pdf_file.name, "")
            
            # Renommer
            success, new_path = self.rename_file(
                pdf_file,
                content=content,
                filename_hint=pdf_file.name
            )
            
            if success:
                stats['success'] += 1
                stats['renames'][pdf_file.name] = Path(new_path).name
            else:
                stats['failed'] += 1
        
        return stats
