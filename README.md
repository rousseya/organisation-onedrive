# Projet d'Organisation des PDFs

Projet Python pour classifier et organiser automatiquement vos fichiers PDFs par catégorie en fonction de leur contenu. Utilise l'API Mistral Vision pour analyser les PDFs numérisés et une base de données SQLite pour le caching et la déduplication.

## Objectifs

- 📁 Scanner tous les PDFs d'un dossier
- 🔍 Analyser le contenu avec AI Vision (Mistral)
- 🏷️ Classifier automatiquement par catégorie
- 📂 Organiser les fichiers dans des dossiers par catégorie
- 💾 Cacher les PDFs traités pour optimiser les re-runs
- 🔐 Détecter les doublons via hachage (MD5 + Perceptual Hash)

## Installation

### Prérequis

- [uv](https://docs.astral.sh/uv/) - Le gestionnaire de paquets et projets Python ultra-rapide d'Astral
- Python 3.8+ (uv gérera automatiquement la version)

### Installation de UV

```bash
# Sur Windows avec pip
pip install uv

# Ou via le script d'installation officiel
# https://docs.astral.sh/uv/getting-started/installation/
```

### Configuration du projet

1. Clonez ou téléchargez le projet

2. Initialisez l'environnement virtuel et installez les dépendances avec uv:

```bash
uv sync
```

3. Copiez le fichier `.env.example` en `.env` et ajustez les paramètres:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

## Utilisation avec UV

### Exécuter le script d'organisation

```bash
# Méthode 1 : Via uv run (plus simple)
uv run organize_pdfs.py

# Méthode 2 : Activer l'environnement virtuel d'abord
.venv-1\Scripts\Activate.ps1    # Windows PowerShell
source .venv-1/bin/activate     # Linux/Mac
python organize_pdfs.py
```

### Ajouter des dépendances

```bash
# Ajouter une nouvelle dépendance
uv add pydantic

# Ajouter une dépendance de développement
uv add --dev pytest
```

```bash
# Mettre à jour toutes les dépendances
uv sync --upgrade

# Mettre à jour le fichier lock
uv lock --upgrade
```

## Configuration

Modifiez le fichier `.env` pour adapter les chemins et options :

```env
PDF_SOURCE_PATH=/mnt/c/Users/rouss/OneDrive/Documents
PDF_OUTPUT_PATH=/mnt/c/Users/rouss/OneDrive/MyPDFs
MOVE_FILES=False                 # True pour déplacer, False pour copier
RENAME_FILES=True                # True pour renommer intelligemment
CONFIG_FILE=config/categories.json
AI_API_KEY=<votre-clé-mistral>  # Clé API Mistral pour l'analyse IA
USE_AI_ANALYSIS=True             # True pour analyser les PDFs avec l'IA Vision
CREATE_FOLDERS=True              # True pour créer les dossiers de catégorie
```

### Configuration Mistral AI

Pour utiliser l'analyse AI Vision sur les PDFs numérisés:

1. Obtenez une clé API sur [console.mistral.ai](https://console.mistral.ai)
2. Ajoutez la clé dans `.env` : `AI_API_KEY=votre-clé-api`
3. Activez l'analyse : `USE_AI_ANALYSIS=True`

**Modèles utilisés:**
- `pixtral-12b-2409` - Vision API pour analyser les images PDF
- `mistral-medium` - Chat pour la classification textuelle

### Options de renommage

- **RENAME_FILES=True** (par défaut)
  - Les fichiers sont renommés avec des noms significatifs
  - ASCII uniquement (pas d'accents ou caractères spéciaux)
  - Maximum 30 caractères (y compris l'extension .pdf)
  - Les espaces sont remplacés par des underscores
  
Exemples de renommage :
```
Avant: 2024-06-09_065768 vaccination.pdf
Après: 2024.pdf

Avant: passeport-yann-rousseau.pdf
Après: passeport_yann_rousseau.pdf

Avant: randonnee-la-cascade-de-clars-via-l-ubac-de-braine.pdf
Après: verdon_aretedelapattedeche.pdf
```

### Catégories

Les catégories sont définies dans `config/categories.json`. Vous pouvez les personnaliser en ajoutant ou modifiant des catégories et leurs mots-clés.

Exemple:
```json
{
  "categories": {
    "Santé": {
      "keywords": ["vaccination", "vaccin", "médecin", "santé"],
      "folder": "Santé"
    },
    "Finances": {
      "keywords": ["facture", "invoice", "paiement", "bancaire"],
      "folder": "Finances"
    }
  }
}
```

## Structure du projet

```
organisation-onedrive/
├── src/
│   ├── __init__.py
│   ├── pdf_extractor.py            # Extraction du contenu et hachage des PDFs
│   ├── pdf_classifier.py           # Classification par catégorie (keywords + AI)
│   ├── pdf_database.py             # Gestion SQLite, caching et déduplication
│   ├── pdf_organizer.py            # Organisation des fichiers
│   ├── pdf_documentation.py        # Génération de markdown avec métadonnées
│   ├── pdf_renamer.py              # Renommage intelligent des fichiers
│   ├── pdf_ai_analyzer.py          # Analyseur IA (version stable)
│   └── pdf_ai_analyzer_v2.py       # Analyseur IA avec Mistral Vision
├── config/
│   └── categories.json             # Configuration des catégories et keywords
├── organize_pdfs.py                # Script principal d'organisation
├── pyproject.toml                  # Configuration du projet et dépendances
├── uv.lock                         # Verrous des dépendances (versionning reproductible)
├── .python-version                 # Version Python pour uv (3.13.0)
├── .env                            # Configuration (ne pas commiter)
├── .env.example                    # Exemple de configuration
├── .gitignore                      # Fichiers à ignorer dans git
└── README.md                       # Ce fichier
```

## Utilisation SQLite

Le script génère automatiquement une base de données `pdfs_inventory.db` pour le caching et la déduplication.

### Requêtes utiles

```bash
# Installer sqlite3 (si nécessaire)
sudo apt install sqlite3

# Voir le nombre total de PDFs
sqlite3 /chemin/vers/pdfs_inventory.db "SELECT COUNT(*) as total FROM pdfs;"

# Lister tous les PDFs d'une catégorie
sqlite3 /chemin/vers/pdfs_inventory.db "SELECT organized_filename, category FROM pdfs WHERE category='Santé';"

# Trouver les PDFs par confiance
sqlite3 /chemin/vers/pdfs_inventory.db "SELECT organized_filename, confidence FROM pdfs WHERE confidence < 0.8;"

# Détecter les doublons exacts (même MD5)
sqlite3 /chemin/vers/pdfs_inventory.db "SELECT md5_hash, COUNT(*) FROM pdfs GROUP BY md5_hash HAVING COUNT(*) > 1;"

# Voir toutes les sources d'un PDF
sqlite3 /chemin/vers/pdfs_inventory.db "SELECT organized_filename, source_paths FROM pdfs LIMIT 5;"
```

**Schema de la table `pdfs`:**
- `md5_hash` - Identifiant unique (exact duplicate detection)
- `perceptual_hash` - Empreinte de similarité
- `original_filename` - Nom avant renommage
- `organized_filename` - Nom après renommage
- `category` - Catégorie assignée
- `source_paths` - Emplacements originels (JSON array)
- `confidence` - Score de confiance de la classification
- `organized_path` - Chemin complet du fichier
- `processing_date` - Date de traitement initial
- `last_updated` - Dernière mise à jour

## Fonctionnement

### PDFExtractor
- Extrait le texte de chaque page du PDF
- Limite l'extraction aux 2 premières pages pour la performance
- Convertit le texte en minuscules
- Extrait aussi les métadonnées (titre, sujet, auteur, nombre de pages)
- **Calcule MD5 hash** pour la détection exacte des doublons
- **Calcule Perceptual Hash** pour la détection de documents similaires

### PDFClassifier
- Charge les catégories et keywords depuis la configuration
- Analyse d'abord le nom du fichier et le contenu (keywords)
- En cas d'échec, utilise **Mistral Vision AI** pour analyser les images PDF
- Calcule un score de correspondance pour chaque catégorie
- Retourne la catégorie la mieux notée avec le score de confiance
- Classe en "Autre" si aucune correspondance

### PDFDatabase
- **Caching intelligent**: stocke les PDFs traités avec leurs métadonnées
- Utilise MD5 pour identifier rapidement les PDFs déjà organisés
- Évite la retraitement lors des re-runs (gain de 90% de temps)
- Suit les sources multiples (JSON array) pour chaque PDF
- Détecte les doublons exacts (MD5) et similaires (Perceptual Hash)
- Base de données SQLite à: `PDF_OUTPUT_PATH/pdfs_inventory.db`

### PDFOrganizer
- Crée les dossiers pour chaque catégorie
- Copie ou déplace les fichiers selon la configuration
- **Renomme optionnellement les fichiers** avec des noms significatifs (ASCII, max 30 caractères)
- Génère des statistiques détaillées

### PDFDocumentation
- Génère un fichier Markdown pour chaque PDF avec:
  - Description du document
  - Métadonnées (titre, auteur, pages)
  - **Source**: liste des emplacements originels du PDF
  - **Integrity & Deduplication**: MD5 et Perceptual Hash pour audit

### PDFRenamer
- Génère des noms significatifs basés sur le contenu et le nom original du PDF
- Convertit les accents en ASCII (é → e, ç → c, etc.)
- Remplace les espaces par des underscores
- Limite les noms à 30 caractères maximum (avec extension .pdf)
- Évite les collisions en ajoutant un suffixe numérique si nécessaire

## Développement avec UV

### Commandes courantes

```bash
# Afficher les informations du projet
uv project

# Nettoyer les caches
uv cache clean

# Vérifier les vulnerabilités des dépendances
uv pip audit

# Créer un script standalone
uv build
```

### Commandes de virtualenv

```bash
# Afficher le chemin du virtualenv
uv venv --path

# Recréer le virtualenv
uv venv --refresh

# Utiliser une version Python spécifique
uv venv --python 3.11
```

## Améliorations futures

- [ ] Conditions markdown regeneration sur changement de source
- [ ] Intégration de la recherche de similarité dans le workflow principal
- [ ] Archivage automatique des PDFs supprimés de la source
- [ ] Interface graphique (GUI)
- [ ] Support des formats autres que PDF (DOCX, Images, etc.)
- [ ] API REST pour l'intégration
- [ ] Machine learning avec apprentissage à partir des classifications

## Dépendances

- **pdfplumber** - Extraction de texte à partir de PDFs
- **python-dotenv** - Gestion des variables d'environnement
- **pdf2image** - Conversion PDF → images (pour la Vision AI)
- **requests** - HTTP client pour l'API Mistral
- **Pillow** - Traitement d'images

### Dépendances système

- **SQLite3** - Base de données (incluse dans Python)
- **libpoppler** (optionnel) - Pour pdf2image (Windows: gratuit, Linux: `sudo apt install libpoppler-cpp-dev`)

Voir `pyproject.toml` pour plus de détails et `uv.lock` pour les versions exactes.

## Licence

MIT

## Support

Pour toute question ou problème:
- Consultez les logs affichés lors de l'exécution
- Vérifiez la configuration dans `.env`
- Interrogez la base de données SQLite pour le debugging
- Consultez `config/categories.json` pour les catégories

## Ressources

- [Documentation UV](https://docs.astral.sh/uv/)
- [Documentation Mistral AI](https://docs.mistral.ai/)
- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)

