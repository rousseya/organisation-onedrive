"""
Script principal pour organiser les PDFs
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Ajouter le chemin du package
sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_extractor import PDFExtractor
from src.pdf_classifier import PDFClassifier
from src.pdf_organizer import PDFOrganizer
from src.pdf_renamer import PDFRenamer
from src.pdf_documentation import PDFDocumentationGenerator
from src.pdf_database import PDFDatabase

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('organization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()


def main():
    """Fonction principale"""
    
    # Charger la configuration
    pdf_source_path = os.getenv('PDF_SOURCE_PATH', r'C:\Users\rouss\OneDrive\Documents')
    pdf_output_path = os.getenv('PDF_OUTPUT_PATH', r'C:\Users\rouss\OneDrive\Documents\Organisé')
    config_file = os.getenv('CONFIG_FILE', 'config/categories.json')
    move_files = os.getenv('MOVE_FILES', 'False').lower() == 'true'
    rename_files = os.getenv('RENAME_FILES', 'True').lower() == 'true'
    
    logger.info("=" * 60)
    logger.info("Démarrage de l'organisation des PDFs")
    logger.info(f"Source: {pdf_source_path}")
    logger.info(f"Destination: {pdf_output_path}")
    logger.info(f"Mode: {'DÉPLACEMENT' if move_files else 'COPIE'}")
    logger.info(f"Renommage: {'ACTIVÉ' if rename_files else 'DÉSACTIVÉ'}")
    logger.info("=" * 60)
    
    try:
        # Initialiser les composants
        source_path = Path(pdf_source_path)
        output_path = Path(pdf_output_path)
        
        if not source_path.exists():
            logger.error(f"Le dossier source n'existe pas: {source_path}")
            return False
        
        # Initialiser la base de données
        db_path = output_path / "pdfs_inventory.db"
        database = PDFDatabase(db_path)
        
        # Trouver tous les PDFs
        pdf_files = list(source_path.glob("*.pdf"))
        logger.info(f"Trouvé {len(pdf_files)} fichiers PDF")
        
        if not pdf_files:
            logger.warning("Aucun fichier PDF trouvé")
            return False
        
        # Initialiser les extracteurs et classificateurs
        extractor = PDFExtractor()
        classifier = PDFClassifier(config_file)
        organizer = PDFOrganizer(output_path, move_files=move_files, rename_files=rename_files)
        doc_generator = PDFDocumentationGenerator(output_path)
        
        # Traiter chaque PDF
        pdf_data = []
        logger.info("-" * 60)
        logger.info("Extraction et classification des PDFs...")
        logger.info("-" * 60)
        
        for pdf_file in pdf_files:
            try:
                logger.info(f"\nTraitement: {pdf_file.name}")
                
                # Calculer le hash MD5
                md5_hash = extractor.calculate_md5(pdf_file)
                
                # Vérifier si le PDF a déjà été traité
                existing_record = database.get_pdf_record(md5_hash)
                
                if existing_record:
                    # PDF déjà traité
                    logger.info(f"  ✓ PDF déjà organisé (hash: {md5_hash[:8]}...)")
                    
                    # Vérifier si la source a changé
                    import json
                    existing_sources = json.loads(existing_record['source_paths'])
                    current_source = str(pdf_file)
                    
                    if current_source not in existing_sources:
                        logger.info(f"  ℹ Source mise à jour - MD: {existing_record['organized_filename']}")
                        database.update_source_path(md5_hash, current_source)
                    
                    # Récupérer les données existantes
                    pdf_data_item = {
                        'path': pdf_file,
                        'category': existing_record['category'],
                        'filename': existing_record['original_filename'],
                        'confidence': existing_record['confidence'] / 100 if existing_record['confidence'] else 0,
                        'content': '',
                        'ai_result': {
                            'document_type': existing_record['document_type'],
                            'source': 'database_cache',
                            'reason': 'Retrieved from cache'
                        },
                        'renamed_filename': existing_record['organized_filename'],
                        'md5_hash': md5_hash,
                        'perceptual_hash': existing_record['perceptual_hash'],
                        'from_cache': True
                    }
                    pdf_data.append(pdf_data_item)
                    logger.info(f"  Catégorie: {existing_record['category']} (cache)")
                else:
                    # PDF nouveau - traiter normalement
                    logger.info(f"  Nouveau PDF - extraction et classification...")
                    
                    # Extraire le contenu
                    content = extractor.extract_text(pdf_file)
                    metadata = extractor.extract_metadata(pdf_file)
                    perceptual_hash = extractor.calculate_perceptual_hash(pdf_file)
                    
                    # Classifier (passing PDF path for vision analysis) - get full details
                    classification_result = classifier.classify_with_details(str(pdf_file), pdf_file.name, content)
                    category = classification_result['category']
                    confidence = classification_result['confidence'] / 100  # Convert back to 0-1 scale
                    ai_result = classification_result.get('ai_result', {})
                    
                    logger.info(f"  Catégorie: {category} (confiance: {confidence:.2%})")
                    logger.info(f"  Pages: {metadata.get('pages', 'N/A')}")
                    
                    pdf_data.append({
                        'path': pdf_file,
                        'category': category,
                        'filename': pdf_file.name,
                        'confidence': confidence,
                        'content': content,
                        'ai_result': ai_result,
                        'md5_hash': md5_hash,
                        'perceptual_hash': perceptual_hash,
                        'from_cache': False
                    })
            except Exception as e:
                logger.error(f"Erreur lors du traitement de {pdf_file.name}: {str(e)}", exc_info=True)
                continue
        
        # Organiser les fichiers
        logger.info("-" * 60)
        logger.info("Organisation des fichiers...")
        logger.info("-" * 60)
        
        stats = organizer.organize(pdf_data)
        
        # Sauvegarder dans la base de données
        logger.info("-" * 60)
        logger.info("Sauvegarde dans la base de données...")
        logger.info("-" * 60)
        
        for item in pdf_data:
            if not item.get('from_cache', False):  # Only save new items
                database.add_pdf_record({
                    'md5_hash': item.get('md5_hash'),
                    'perceptual_hash': item.get('perceptual_hash'),
                    'original_filename': item.get('filename'),
                    'category': item.get('category'),
                    'organized_filename': item.get('renamed_filename', item.get('filename')),
                    'organized_path': str(Path(output_path) / item.get('category') / (item.get('renamed_filename', item.get('filename')).replace('.pdf', '') + '.pdf')),
                    'source_paths': [str(item.get('path'))],
                    'confidence': item.get('confidence', 0) * 100,
                    'document_type': item.get('ai_result', {}).get('document_type', 'Unknown')
                })
        
        # Afficher les statistiques de la base de données
        db_stats = database.get_statistics()
        logger.info(f"Base de données - Total PDFs uniques: {db_stats.get('unique_pdfs', 0)}")
        logger.info(f"Base de données - Taille: {db_stats.get('db_size', 0) / 1024:.1f} KB")
        
        # Générer la documentation
        logger.info("-" * 60)
        logger.info("Génération de la documentation...")
        logger.info("-" * 60)
        
        doc_stats = doc_generator.generate_batch_documentation(pdf_data)
        logger.info(f"Documentation générée: {doc_stats['success']} fichiers")
        
        # Afficher les statistiques
        logger.info("-" * 60)
        logger.info("STATISTIQUES")
        logger.info("-" * 60)
        logger.info(f"Total traité: {stats['total']}")
        logger.info(f"Succès: {stats['success']}")
        logger.info(f"Échecs: {stats['failed']}")
        logger.info("\nPar catégorie:")
        
        for category, count in sorted(stats['by_category'].items()):
            logger.info(f"  {category}: {count} fichier(s)")
        
        logger.info("=" * 60)
        logger.info("Organisation terminée avec succès!")
        logger.info("=" * 60)
        
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de l'organisation: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
