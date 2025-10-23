# Assistant Réglementaire Automobile

Assistant IA de nouvelle génération spécialisé dans les réglementations automobiles UN/ECE, utilisant une architecture RAG (Retrieval-Augmented Generation) avancée avec interface Streamlit moderne et intuitive.

## Fonctionnalités

- **Interface conversationnelle intelligente** : Chat interactif avec contexte multi-tour pour des questions complexes
- **Recherche multimodale avancée** : Récupération simultanée depuis texte, images et tableaux avec validation LLM
- **Mémoire conversationnelle** : Maintien et résumé automatique du contexte sur plusieurs échanges
- **Validation et reranking** : Vérification LLM de la pertinence + reranking optionnel (Jina API)
- **Support multilingue** : Interface complète en français et anglais avec i18n
- **Export professionnel** : Génération de rapports PDF détaillés des conversations
- **Authentification moderne** : Système d'authentification avec gestion des utilisateurs et permissions
- **Configuration flexible** : Interface de configuration complète pour tous les paramètres

## Architecture Technique

Le système repose sur une **architecture RAG modulaire** de dernière génération avec séparation claire des responsabilités :

### Composants Principaux

#### 1. **ModularOrchestrator** (Orchestrateur Principal)
- **Localisation** : `assistant_regulation/planning/Orchestrator/modular_orchestrator.py`
- **Rôle** : Coordination centralisée de tous les services
- **Avantages** :
  - Modularité et extensibilité accrues
  - Gestion intelligente du routing des requêtes
  - Intégration transparente de la mémoire conversationnelle
  - Remplacement de l'ancien `SimpleOrchestrator` (deprecated)

#### 2. **Services Modulaires** (`assistant_regulation/planning/services/`)
Architecture orientée services avec responsabilités claires :

| Service | Responsabilité | Fichier |
|---------|----------------|---------|
| **RetrievalService** | Recherche multimodale (texte/images/tableaux) | `retrieval_service.py` |
| **GenerationService** | Génération de réponses LLM (Ollama/Mistral/OpenAI) | `generation_service.py` |
| **MemoryService** | Gestion du contexte conversationnel | `memory_service.py` |
| **ValidationService** | Validation LLM de la pertinence des chunks | `validation_service.py` |
| **ContextBuilderService** | Construction de prompts contextuels | `context_builder_service.py` |
| **RerankerService** | Reranking optionnel avec Jina API | `reranker_service.py` |
| **MasterRoutingService** | Analyse et routage intelligent des requêtes | `master_routing_service.py` |
| **CitationService** | Génération de citations et références | `citation_service.py` |

#### 3. **Système de Chunking Avancé** (Late Chunker via chonkie)
- **Localisation** : `assistant_regulation/processing/Modul_Process/chunking_text.py`
- **Technologie** : [chonkie](https://github.com/bhavnicksm/chonkie) avec Late Chunker
- **Performance** : 15x plus rapide que l'ancien système Docling
- **Avantages** :
  - Préservation du contexte global sur tout le document
  - Cohérence sémantique optimale pour documents réglementaires
  - Métadonnées enrichies (qualité, type de contenu, scores)
  - Gestion intelligente des références croisées

#### 4. **Retrievers Multimodaux** (`assistant_regulation/processing/Modul_emb/`)
- **TextRetriever** : Recherche sémantique sur chunks textuels
- **ImageRetriever** : Recherche sur images avec descriptions AI
- **TableRetriever** : Recherche sur tableaux structurés
- **BaseRetriever** : Classe abstraite commune

#### 5. **Pipeline de Traitement** (`assistant_regulation/processing/`)
- Ingestion de PDFs réglementaires
- Extraction multimodale (texte, images, tableaux)
- Génération d'embeddings avec sentence-transformers
- Stockage dans ChromaDB (collections séparées par type)

### Flux de Données

```
PDF Documents
    ↓
[Late Chunker] → Chunks (texte/images/tableaux)
    ↓
[Embedding Generation] → Vecteurs
    ↓
[ChromaDB Storage] → Collections vectorielles
    ↓
User Query → [ModularOrchestrator]
    ↓
[MasterRoutingService] → Analyse de requête
    ↓
[RetrievalService] → Recherche multimodale
    ↓
[ValidationService] → Filtrage LLM
    ↓
[RerankerService] (optionnel) → Reranking
    ↓
[ContextBuilderService] → Construction de prompt
    ↓
[MemoryService] → Intégration historique
    ↓
[GenerationService] → Réponse LLM finale
    ↓
User Response + Sources + Images
```

## Prérequis

### Système
- **Python** : Version 3.10+ (testé sur Python 3.13.5)
- **Espace disque** : ~5-10 GB pour bases vectorielles et cache
- **RAM** : Minimum 8 GB (16 GB recommandé pour performances optimales)

### LLM Provider (choisir au moins un)
- **Option 1 - Ollama** (local, gratuit) : Installation requise → [ollama.ai](https://ollama.ai)
- **Option 2 - Mistral AI** (cloud) : Clé API requise → [console.mistral.ai](https://console.mistral.ai)
- **Option 3 - OpenAI** (cloud) : Clé API requise → [platform.openai.com](https://platform.openai.com)

### Services Optionnels
- **Jina AI** : Pour reranking avancé → [jina.ai](https://jina.ai) (optionnel)

## Installation

### 1. Cloner le projet
```bash
git clone https://github.com/Franlao/Assistant_regulation.git
cd Assistant_regulation
```

### 2. Créer un environnement virtuel (recommandé)
```bash
# Créer l'environnement
python -m venv venv

# Activer l'environnement
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

**Important** : Le système de chunking nécessite `chonkie` avec support Streamlit :
```bash
pip install 'chonkie[st]'
```

### 4. Configuration des clés API (optionnel)

Créer un fichier `.env` à la racine du projet :

```bash
# === LLM Providers (au moins un requis) ===
MISTRAL_API_KEY=votre_cle_mistral_ici
OPENAI_API_KEY=votre_cle_openai_ici

# === Services optionnels ===
JINA_API_KEY=votre_cle_jina_ici

# === Configuration Streamlit ===
STREAMLIT_SERVER_TIMEOUT=300
```

**Note** : Un fichier `.env.example` est fourni comme modèle

### 5. Préparer les données

#### Option A : Traitement initial complet
```bash
# Traiter tous les PDFs du dossier Data/
python -m assistant_regulation.processing.process_regulations
```

#### Option B : Régénération rapide (texte uniquement)
```bash
# Plus rapide, idéal pour développement
python -m assistant_regulation.processing.process_regulations --regenerate --text-only
```

#### Option C : Traitement parallèle (recommandé pour production)
```bash
# Utilise plusieurs workers pour plus de rapidité
python -m assistant_regulation.processing.process_regulations --regenerate-parallel --workers 4
```

#### Option D : Test de configuration
```bash
# Vérifier que tout est correctement configuré
python -m assistant_regulation.processing.process_regulations --test
```

## Démarrage

### Lancement de l'application

```bash
streamlit run app.py
```

L'interface web sera accessible à l'adresse : **http://localhost:8501**

### Configuration via l'interface

Au premier démarrage, configurer les paramètres via la barre latérale :

#### 1. **Provider LLM** (onglet Configuration → LLM)
- Choisir entre **Ollama** (local), **Mistral AI** (cloud), ou **OpenAI**
- Sélectionner le modèle souhaité :
  - **Ollama** : `llama3.2`, `mistral`, `granite3.1-moe:3b`
  - **Mistral** : `mistral-medium`, `mistral-large-latest`
  - **OpenAI** : `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`

#### 2. **Options RAG** (onglet Configuration → RAG)
- **Activer images** : Inclure les diagrammes et schémas
- **Activer tableaux** : Inclure les données tabulaires
- **Vérification LLM** : Validation de pertinence (recommandé, mais plus lent)
- **Seuil de confiance** : 0.0 à 1.0 (défaut: 0.45)
- **Reranking** : Activer Jina pour reranking avancé

#### 3. **Mémoire conversationnelle** (onglet Configuration → Memory)
- **Taille de fenêtre** : Nombre de messages conservés (défaut: 5)
- Résumé automatique au-delà de la limite

#### 4. **Interface utilisateur** (onglet Configuration → UI)
- **Langue** : Français / English
- **Limite d'affichage** : Nombre de sources montrées

### Premier usage

1. Poser une question dans le chat (exemple : "Quelles sont les dimensions des rétroviseurs de Classe III selon R046 ?")
2. Observer les sources récupérées dans la barre latérale
3. Consulter les images et tableaux pertinents
4. Exporter la conversation en PDF si besoin

## Structure du Projet

```
Assistant_regulation/
│
├── app.py                                 # Point d'entrée Streamlit principal
├── requirements.txt                       # Dépendances Python optimisées
├── .env.example                           # Template configuration environnement
├── CLAUDE.md                              # Instructions pour Claude Code
├── README.md                              # Documentation (ce fichier)
│
├── config/                                # Configuration centralisée
│   ├── config.py                          # Classes de configuration (dataclasses)
│   └── config.json                        # Paramètres par défaut (auto-généré)
│
├── pages/                                 # Pages Streamlit secondaires
│   ├── configuration.py                   # Interface de configuration complète
│   ├── database.py                        # Gestion base de données et ingestion
│   └── summary.py                         # Génération de résumés de documents
│
├── components/                            # Composants réutilisables
│   ├── modern_auth_integration.py         # Système d'authentification moderne
│   ├── auth_components.py                 # Composants auth basiques
│   ├── folder_selector.py                 # Sélecteur de dossiers
│   ├── task_monitor.py                    # Monitoring des tâches longues
│   └── custom_language_selector/          # Sélecteur de langue personnalisé
│
├── assistant_regulation/                  # Code source principal
│   │
│   ├── app/                               # Interface utilisateur Streamlit
│   │   ├── chat_generation.py            # Génération et affichage du chat
│   │   ├── display_components.py         # Composants d'affichage génériques
│   │   ├── display_manager.py            # Gestion centralisée de l'affichage
│   │   ├── main_content.py               # Contenu principal de la page
│   │   ├── sidebar_components.py         # Composants barre latérale
│   │   ├── source_display.py             # Affichage des sources récupérées
│   │   ├── streamlit_utils.py            # Utilitaires Streamlit
│   │   ├── ui_styles.py                  # Styles CSS personnalisés
│   │   └── data_extraction.py            # Extraction de données UI
│   │
│   ├── planning/                          # Orchestration et intelligence
│   │   │
│   │   ├── Orchestrator/                  # Orchestrateurs principaux
│   │   │   └── modular_orchestrator.py   # ModularOrchestrator (principal, v3)
│   │   │
│   │   ├── services/                      # Services modulaires (architecture SOA)
│   │   │   ├── retrieval_service.py      # Recherche multimodale
│   │   │   ├── generation_service.py     # Génération LLM
│   │   │   ├── memory_service.py         # Gestion mémoire conversationnelle
│   │   │   ├── validation_service.py     # Validation LLM des chunks
│   │   │   ├── context_builder_service.py # Construction de prompts
│   │   │   ├── reranker_service.py       # Reranking avec Jina
│   │   │   ├── master_routing_service.py # Routage intelligent principal
│   │   │   ├── citation_service.py       # Génération de citations
│   │   │   ├── prompting_service.py      # Gestion des prompts
│   │   │   ├── intelligent_routing_service.py    # Routage par analyse
│   │   │   ├── knowledge_routing_service.py      # Routage par connaissance
│   │   │   ├── intelligent_summary_service.py    # Résumés intelligents
│   │   │   ├── database_meta_service.py  # Métadonnées de base de données
│   │   │   └── pdf_export_service.py     # Export PDF des conversations
│   │   │
│   │   ├── agents/                        # Agents spécialisés
│   │   │   ├── agent_image.py            # Agent traitement d'images
│   │   │   └── query_analysis_agent.py   # Agent analyse de requêtes
│   │   │
│   │   └── Database/                      # Opérations base de données
│   │       ├── database_summary.py       # Résumés et statistiques DB
│   │       ├── database_cleanup.py       # Nettoyage et maintenance
│   │       ├── pdf_ingestion.py          # Ingestion de nouveaux PDFs
│   │       ├── pdf_upload.py             # Upload et validation PDFs
│   │       ├── regulation_search.py      # Recherche dans réglementations
│   │       └── list_regulations.py       # Listing des documents disponibles
│   │
│   ├── processing/                        # Traitement des documents
│   │   │
│   │   ├── process_regulations.py        # Pipeline principal de traitement
│   │   │
│   │   ├── Modul_Process/                # Modules de traitement
│   │   │   ├── chunking_text.py          # Late Chunker (chonkie)
│   │   │   ├── extract_images.py         # Extraction d'images
│   │   │   ├── extract_tables.py         # Extraction de tableaux
│   │   │   └── clean_cache.py            # Nettoyage du cache
│   │   │
│   │   ├── Modul_emb/                    # Retrievers et embeddings
│   │   │   ├── base_retriever.py         # Classe abstraite de base
│   │   │   ├── text_retriever.py         # Retriever texte
│   │   │   ├── image_retriever.py        # Retriever images
│   │   │   └── table_retriever.py        # Retriever tableaux
│   │   │
│   │   └── Modul_verif/                  # Vérification et validation
│   │       └── agent_verif.py            # Agent de vérification LLM
│   │
│   ├── utils/                             # Utilitaires généraux
│   │   ├── session_utils.py              # Gestion session Streamlit
│   │   └── i18n_migration_helper.py      # Helper migration i18n
│   │
│   └── static/                            # Fichiers statiques
│       ├── styles.css                    # Styles CSS globaux
│       └── images/                       # Images de l'interface
│
├── translations/                          # Internationalisation (i18n)
│   ├── __init__.py                       # Initialisation i18n
│   ├── fr.json                           # Traductions françaises
│   └── en.json                           # Traductions anglaises
│
├── Data/                                  # Documents réglementaires (PDFs)
│   └── *.pdf                             # 47 réglementations UN/ECE
│
├── DB/                                    # Bases de données ChromaDB
│   ├── regulations_text/                 # Collection texte
│   ├── regulations_images/               # Collection images
│   └── regulations_tables/               # Collection tableaux
│
├── Cache et données runtime
│   ├── joblib_cache/                     # Cache joblib pour retrievers
│   ├── image_cache/                      # Cache des images extraites
│   ├── .conversation_memory/             # Mémoire conversationnelle
│   └── logs/                             # Logs applicatifs
│
├── tests/                                 # Suite de tests pytest
│   ├── test_config.py                    # Tests configuration
│   ├── test_services.py                  # Tests services
│   ├── test_orchestrator.py             # Tests orchestrateur
│   ├── test_processing.py               # Tests traitement
│   ├── test_app_components.py           # Tests composants UI
│   └── test_integration.py              # Tests d'intégration
│
├── scripts/                               # Scripts utilitaires
│   └── *.sh / *.py                       # Scripts de maintenance
│
└── Déploiement
    ├── railway.json                      # Configuration Railway
    ├── railway-build.sh                  # Script de build Railway
    ├── Procfile                          # Configuration Heroku/Railway
    └── RAILWAY_DEPLOY.md                 # Guide de déploiement
```

### Fichiers Clés

| Fichier | Description | Importance |
|---------|-------------|------------|
| `app.py` | Point d'entrée principal de l'application | Critique |
| `assistant_regulation/planning/Orchestrator/modular_orchestrator.py` | Orchestrateur principal (v3) | Critique |
| `assistant_regulation/processing/process_regulations.py` | Pipeline de traitement des PDFs | Critique |
| `assistant_regulation/processing/Modul_Process/chunking_text.py` | Late Chunker (chonkie) | Critique |
| `config/config.py` | Système de configuration centralisé | Important |
| `pages/configuration.py` | Interface de configuration complète | Important |
| `translations/*.json` | Fichiers de traduction i18n | Important |

## Configuration Avancée

### Providers LLM Supportés

Le système supporte trois providers avec sélection dynamique :

#### **1. Ollama** (Local - Gratuit)
```bash
# Installation Ollama
# Windows/Mac : https://ollama.ai/download
# Linux : curl -fsSL https://ollama.ai/install.sh | sh

# Télécharger des modèles
ollama pull llama3.2
ollama pull mistral
ollama pull granite3.1-moe:3b
```

**Modèles recommandés** :
- `llama3.2` : Excellent équilibre performance/qualité
- `mistral` : Rapide et efficace pour le français
- `granite3.1-moe:3b` : Léger, idéal pour ressources limitées

#### **2. Mistral AI** (Cloud)
**Modèles disponibles** :
- `mistral-medium` : Bon rapport qualité/prix
- `mistral-large-latest` : Maximum de qualité
- `mistral-small` : Économique pour tests

**Configuration** : Ajouter `MISTRAL_API_KEY` dans `.env`

#### **3. OpenAI** (Cloud)
**Modèles disponibles** :
- `gpt-4o` : Meilleure qualité
- `gpt-4-turbo` : Rapide et performant
- `gpt-3.5-turbo` : Économique

**Configuration** : Ajouter `OPENAI_API_KEY` dans `.env`

### Variables d'Environnement

Fichier `.env` complet :

```bash
# ===== LLM PROVIDERS =====
# Mistral AI (cloud)
MISTRAL_API_KEY=votre_cle_mistral

# OpenAI (cloud)
OPENAI_API_KEY=votre_cle_openai

# ===== SERVICES OPTIONNELS =====
# Jina AI (pour reranking avancé)
JINA_API_KEY=votre_cle_jina

# ===== CONFIGURATION STREAMLIT =====
STREAMLIT_SERVER_TIMEOUT=300

# ===== CONFIGURATION RAG (optionnel) =====
RAG_CONFIDENCE_THRESHOLD=0.45
RAG_TOP_K=5
RAG_ENABLE_IMAGES=true
RAG_ENABLE_TABLES=true
RAG_ENABLE_LLM_VERIFICATION=false

# ===== CHEMINS PERSONNALISÉS (optionnel) =====
DATA_PATH=./Data
DB_PATH=./DB
CACHE_PATH=./joblib_cache
```

### Fichier de Configuration (`config/config.json`)

Le système génère automatiquement ce fichier au premier lancement. Il contient :

```json
{
  "llm": {
    "provider": "ollama",
    "ollama_model": "llama3.2",
    "mistral_model": "mistral-large-latest",
    "openai_model": "gpt-4o",
    "ollama_models": ["llama3.2", "mistral", "granite3.1-moe:3b"],
    "mistral_models": ["mistral-medium", "mistral-large-latest"],
    "openai_models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
  },
  "rag": {
    "confidence_threshold": 0.45,
    "enable_images": true,
    "enable_tables": true,
    "enable_llm_verification": false,
    "enable_reranking": false,
    "top_k": 5
  },
  "memory": {
    "conversation_window_size": 5,
    "enable_summarization": true
  },
  "ui": {
    "language": "fr",
    "display_limit": 10
  }
}
```

**Modification** : Éditer directement ou utiliser l'interface de configuration dans l'application.

## Utilisation

### Interface Web Principale

#### Page d'accueil (Chat)
1. Accéder à `http://localhost:8501`
2. Se connecter si l'authentification est activée
3. Configurer les paramètres dans la barre latérale :
   - Sélectionner le provider LLM et le modèle
   - Activer/désactiver images et tableaux
   - Configurer le seuil de confiance
4. Poser des questions dans le chat
5. Observer les sources, images et tableaux récupérés
6. Exporter la conversation en PDF si nécessaire

#### Pages Secondaires

**Configuration** (`/configuration`)
- Configuration complète de tous les paramètres
- Sauvegarde persistante dans `config/config.json`
- Sections : LLM, RAG, Mémoire, UI, Système

**Database** (`/database`)
- État de la base de données ChromaDB
- Ingestion de nouveaux PDFs
- Recherche dans les réglementations
- Nettoyage et maintenance
- Génération de résumés de documents

**Summary** (`/summary`)
- Génération de résumés intelligents de documents
- Comparaison de réglementations
- Export des résumés

### Questions d'Exemple

**Questions simples** :
- "Qu'est-ce que la réglementation R046 ?"
- "Quelles sont les catégories de rétroviseurs ?"

**Questions avec images** :
- "Montre-moi les dimensions des rétroviseurs de Classe III"
- "Affiche le schéma des feux de position arrière"

**Questions avec tableaux** :
- "Quels sont les tests obligatoires pour l'homologation des ceintures de sécurité ?"
- "Donne-moi le tableau des dimensions minimales pour les rétroviseurs"

**Questions complexes multi-tour** :
- Q1: "Quelles sont les exigences pour les rétroviseurs selon R046 ?"
- Q2: "Et pour la classe III spécifiquement ?" (utilise le contexte)
- Q3: "Montre-moi les dimensions exactes" (utilise tout le contexte)

## Documents Supportés

Le système contient **47 réglementations UN/ECE** dans le répertoire `Data/` :

**Principales réglementations** :
- **R046** : Dispositifs de vision indirecte (rétroviseurs)
- **R107** : Autobus et autocars à deux étages
- **R003, R006, R007** : Feux et dispositifs de signalisation
- **R010** : Compatibilité électromagnétique
- **R016** : Ceintures de sécurité
- Et 42 autres réglementations

## Commandes de Développement

### Traitement des Documents

```bash
# Régénération complète (texte + images + tableaux)
python -m assistant_regulation.processing.process_regulations --regenerate

# Régénération rapide (texte uniquement)
python -m assistant_regulation.processing.process_regulations --regenerate --text-only

# Traitement parallèle (4 workers)
python -m assistant_regulation.processing.process_regulations --regenerate-parallel --workers 4

# Nettoyage des collections uniquement
python -m assistant_regulation.processing.process_regulations --clean-only

# Test de l'environnement
python -m assistant_regulation.processing.process_regulations --test
```

### Tests et Qualité

```bash
# Exécuter tous les tests
pytest

# Tests unitaires uniquement
pytest -m unit

# Tests d'intégration uniquement
pytest -m integration

# Tests avec couverture
pytest --cov=assistant_regulation --cov-report=html

# Tests spécifiques
pytest tests/test_config.py
pytest tests/test_services.py

# Mode développement (arrêt au premier échec)
pytest -x --tb=short
```

### Vérification et Debugging

```bash
# Vérifier l'état de ChromaDB
python -c "from assistant_regulation.planning.Database.database_summary import get_database_status; print(get_database_status())"

# Valider la configuration
python -c "from config import get_config; config = get_config(); print('Configuration OK')"

# Tester le système de configuration
python config/config.py

# Nettoyer tous les caches
python -c "from assistant_regulation.processing.Modul_Process.clean_cache import clear_all_caches; clear_all_caches()"

# Lister les modèles disponibles
python -c "from config import get_config; c = get_config(); print('Ollama:', c.llm.ollama_models); print('Mistral:', c.llm.mistral_models)"
```

### Notebooks de Développement

```bash
# Lancer Jupyter
jupyter notebook notebooks/

# Ou JupyterLab
jupyter lab
```

### Logs et Monitoring

```bash
# Voir les logs en temps réel
tail -f logs/app.log

# Logs d'optimisation (activés dans app.py)
# - retrieval_service : cache hits/misses
# - validation_service : filtrage de chunks
# - query_processor : flux complet
```

## Architecture Modulaire et Patterns

### Principes de Design

**Séparation des responsabilités** :
- Chaque service a une responsabilité unique et bien définie
- Communication via interfaces claires
- Dépendances injectées par le ModularOrchestrator

**Configuration centralisée** :
- Un seul point de configuration pour toute l'application
- Support des variables d'environnement
- Validation avec dataclasses Python

**Cache intelligent** :
- Joblib cache pour les résultats de retrieval
- Cache LRU pour les embeddings
- Invalidation automatique quand nécessaire

**Extensibilité** :
- Architecture prête pour l'ajout de nouveaux providers LLM
- Interface abstraite pour les retrievers
- Services modulaires facilement remplaçables

### Ajout d'un Nouveau Provider LLM

```python
# 1. Ajouter le provider dans config/config.py
class LLMConfig:
    # ...
    nouveau_provider_models: list[str] = field(default_factory=lambda: ["model1", "model2"])

# 2. Ajouter la logique dans generation_service.py
def generate_response(self, prompt: str) -> str:
    if self.provider == "nouveau_provider":
        # Logique de génération
        pass

# 3. Mettre à jour l'interface dans pages/configuration.py
# Ajouter l'option dans le sélecteur de provider
```

## Déploiement

### Railway

Le projet est configuré pour un déploiement sur Railway :

```bash
# Le fichier railway.json contient la configuration
# Le script railway-build.sh gère l'installation optimisée

# Déploiement automatique via Git push
git push railway main
```

Voir `RAILWAY_DEPLOY.md` pour les détails complets.

### Docker (à venir)

Un Dockerfile est en cours de préparation pour faciliter le déploiement conteneurisé.

## Dépannage

### Problèmes Courants

**ChromaDB ne trouve pas les collections** :
```bash
# Vérifier l'existence des collections
python -c "from assistant_regulation.planning.Database.database_summary import get_database_status; print(get_database_status())"

# Régénérer si nécessaire
python -m assistant_regulation.processing.process_regulations --regenerate
```

**Erreur de connexion Ollama** :
```bash
# Vérifier qu'Ollama est lancé
ollama list

# Tester une requête
ollama run llama3.2 "Hello"
```

**Erreur de clé API** :
```bash
# Vérifier que le .env est présent et contient les clés
cat .env | grep API_KEY

# Recharger les variables d'environnement
source .env  # Linux/Mac
# ou redémarrer l'application
```

**Performances lentes** :
- Désactiver la vérification LLM (plus rapide)
- Réduire `top_k` dans la configuration RAG
- Utiliser le cache (activé par défaut)
- Activer le reranking uniquement si nécessaire

**Erreurs de mémoire** :
- Réduire la taille de la fenêtre conversationnelle
- Traiter les PDFs en mode `--text-only`
- Augmenter la RAM disponible

## Contribuer

Les contributions sont les bienvenues ! Pour contribuer :

1. Fork le projet
2. Créer une branche pour votre feature (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

### Standards de Code

- Suivre PEP 8 pour le style Python
- Ajouter des docstrings pour les fonctions publiques
- Écrire des tests pour les nouvelles fonctionnalités
- Maintenir la couverture de tests > 80%

## Licence

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contact et Support

- **Issues** : [GitHub Issues](https://github.com/Franlao/Assistant_regulation/issues)
- **Discussions** : [GitHub Discussions](https://github.com/Franlao/Assistant_regulation/discussions)

---

**Dernière mise à jour** : Octobre 2025
**Version** : 3.0 (ModularOrchestrator + Late Chunker)