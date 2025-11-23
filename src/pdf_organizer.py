"""
Module pour organiser les fichiers PDF dans des dossiers par catégorie
"""
import shutil
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


class PDFOrganizer:
    """Classe pour organiser les fichiers PDF"""
    
    def __init__(self, output_path: Path, move_files: bool = False, rename_files: bool = False):
        """
        Initialise l'organisateur
        
        Args:
            output_path: Dossier de destination pour les fichiers organisés
            move_files: Si True, déplace les fichiers; si False, les copie
            rename_files: Si True, renomme les fichiers de manière significative
        """
        self.output_path = Path(output_path)
        self.move_files = move_files
        self.rename_files = rename_files
    
    def organize(self, pdf_data: List[Dict]) -> Dict[str, int]:
        """
        Organise les fichiers PDF dans des dossiers par catégorie
        
        Args:
            pdf_data: Liste de dictionnaires contenant {path, category, filename, content}
        
        Returns:
            Dictionnaire avec les statistiques de l'organisation
        """
        stats = {
            'total': len(pdf_data),
            'success': 0,
            'failed': 0,
            'by_category': {}
        }
        
        # Créer les dossiers par catégorie
        categories = set(item['category'] for item in pdf_data)
        self._create_category_folders(categories)
        
        # Organiser les fichiers
        for item in pdf_data:
            renamed_filename = self._organize_file(
                item['path'], 
                item['category'],
                item.get('content', ''),
                item.get('filename', '')
            )
            if renamed_filename:
                stats['success'] += 1
                category = item['category']
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                # Store the renamed filename for documentation generation
                item['renamed_filename'] = renamed_filename
            else:
                stats['failed'] += 1
        
        return stats
    
    def _create_category_folders(self, categories: set) -> None:
        """Crée les dossiers de catégories"""
        for category in categories:
            category_path = self.output_path / category
            category_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Dossier créé/vérifié: {category_path}")
    
    def _organize_file(self, source_path: Path, category: str, content: str = '', filename: str = '') -> str:
        """
        Déplace ou copie un fichier vers le dossier de sa catégorie
        
        Args:
            source_path: Chemin du fichier source
            category: Catégorie du fichier
            content: Contenu du PDF (utilisé pour renommer)
            filename: Nom original du fichier
        
        Returns:
            Le nom du fichier renommé (sans extension) ou None en cas d'erreur
        """
        try:
            destination_folder = self.output_path / category
            
            # Déterminer le nom du fichier de destination
            if self.rename_files:
                # Importer ici pour éviter les imports circulaires
                from src.pdf_renamer import PDFRenamer
                renamer = PDFRenamer()
                
                # Générer un nouveau nom significatif avec la catégorie comme hint
                new_name = renamer.generate_name_from_content(filename, content, category_hint=category)
                destination_path = destination_folder / f"{new_name}.pdf"
            else:
                destination_path = destination_folder / source_path.name
            
            if destination_path.exists():
                logger.warning(f"Le fichier existe déjà: {destination_path}")
                return destination_path.stem
            
            if self.move_files:
                shutil.move(str(source_path), str(destination_path))
                logger.info(f"Fichier déplacé: {source_path.name} -> {category}/{destination_path.name}")
            else:
                shutil.copy2(str(source_path), str(destination_path))
                logger.info(f"Fichier copié: {source_path.name} -> {category}/{destination_path.name}")
            
            return destination_path.stem
        
        except Exception as e:
            logger.error(f"Erreur lors de l'organisation de {source_path}: {str(e)}")
            return None
