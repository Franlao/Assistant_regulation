# Assistant Réglementaire Automobile

Assistant IA spécialisé dans les réglementations automobiles UN/ECE utilisant une architecture RAG (Retrieval-Augmented Generation) avec interface Streamlit.

## Fonctionnalités

- **Interface conversationnelle** : Chat interactif pour poser des questions sur les réglementations
- **Recherche multimodale** : Récupération d'informations depuis le texte, les images et les tableaux
- **Mémoire conversationnelle** : Maintien du contexte sur plusieurs échanges
- **Vérification LLM** : Validation optionnelle de la pertinence des résultats avant génération
- **Support multilingue** : Interface disponible en français et anglais
- **Export de conversations** : Génération de rapports PDF des échanges

## Architecture

Le système utilise une architecture RAG modulaire :

1. **Traitement** (`assistant_regulation/processing/`) : Ingestion et chunking des documents PDF
2. **Planification** (`assistant_regulation/planning/`) : Orchestration et services de traitement
3. **Interface** (`assistant_regulation/app/`) : Composants Streamlit pour l'UI

### Composants clés
- **Retrievers multimodaux** : BaseRetriever, ImageRetriever, TableRetriever, TextRetriever
- **Orchestrateur principal** : SimpleOrchestrator pour la gestion des workflows
- **Services modulaires** : Récupération, génération, validation, routage intelligent
- **Système de configuration** : Configuration centralisée avec support des variables d'environnement

## Prérequis

- Python 3.10+
- Ollama (local) ou clé API Mistral AI (cloud)
- Espace disque pour les bases de données vectorielles

## Installation

1. **Cloner le projet**
   ```bash
   git clone https://github.com/Franlao/Assistant_regulation.git
   cd Assistant_regulation
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration optionnelle**
   
   Créer un fichier `.env` avec vos clés API (optionnel) :
   ```bash
   MISTRAL_API_KEY=votre_cle_mistral
   JINA_API_KEY=votre_cle_jina
   ```

4. **Initialiser les bases de données vectorielles**
   ```bash
   python -c "from assistant_regulation.processing.process_regulations import process_pdf_directory; process_pdf_directory('./Data')"
   ```

## Démarrage

### Application Streamlit

```bash
streamlit run app.py
```

L'application sera accessible sur `http://localhost:8501`

### Configuration via l'interface

1. **LLM Provider** : Choisir entre Ollama (local) ou Mistral AI
2. **Modèle** : Sélectionner le modèle selon le provider
3. **Options RAG** : Activer/désactiver images, tableaux, vérification
4. **Mémoire** : Configurer la taille de la fenêtre conversationnelle

## Structure du projet

```
Assistant_regulation/
├── app.py                          # Point d'entrée Streamlit
├── requirements.txt                # Dépendances Python
├── config/                         # Configuration centralisée
│   ├── config.py                   # Classes de configuration
│   └── config.json                 # Paramètres par défaut
├── assistant_regulation/           # Code source principal
│   ├── app/                        # Composants UI Streamlit
│   ├── planning/                   # Orchestration et services
│   │   ├── sync/                   # Orchestrateur synchrone
│   │   ├── services/               # Services modulaires
│   │   └── langgraph/              # Workflow avancé (expérimental)
│   └── processing/                 # Traitement des documents
│       ├── Modul_Process/          # Chunking et extraction
│       ├── Modul_emb/              # Retrievers vectoriels
│       ├── Modul_verif/            # Agent de vérification
│       └── Modul_Summary/          # Génération de résumés
├── Data/                           # Documents PDF réglementaires
├── translations/                   # Support multilingue
├── examples/                       # Exemples d'utilisation
└── notebooks/                      # Notebooks de développement
```

## Configuration avancée

### Providers LLM supportés

- **Ollama** (local) : llama3.2, mistral, granite3.1-moe:3b
- **Mistral AI** (cloud) : mistral-medium, mistral-large-latest

### Variables d'environnement

```bash
# Clés API
MISTRAL_API_KEY=                    # Pour Mistral AI
JINA_API_KEY=                       # Pour le reranking (optionnel)

# Configuration Streamlit
STREAMLIT_SERVER_TIMEOUT=300
```

### Fichier de configuration

Le système génère automatiquement `config/config.json` avec tous les paramètres configurables :
- Providers et modèles LLM
- Paramètres RAG (seuils, mots-clés forcés)
- Configuration mémoire conversationnelle
- Paramètres UI (langues, thèmes)

## Utilisation

### Interface web

1. Accéder à `http://localhost:8501`
2. Configurer les paramètres dans la barre latérale
3. Poser des questions sur les réglementations automobiles
4. Consulter les sources et images récupérées
5. Exporter la conversation en PDF si nécessaire

### Questions d'exemple

- "Quelles sont les exigences pour les rétroviseurs de Classe III selon R046 ?"
- "Montre-moi les dimensions des feux de position arrière"
- "Quels sont les tests obligatoires pour l'homologation des ceintures de sécurité ?"

## Documents supportés

Le répertoire `Data/` contient 47 documents PDF de réglementations UN/ECE, incluant :
- R046 (Rétroviseurs)
- R107 (Autobus et autocars)
- R003, R006, R007 (Feux et signalisation)
- Et bien d'autres réglementations automobiles

## Développement

### Tests et validation

```bash
# Test de la configuration
python config/config.py

# Notebooks de développement
jupyter notebook notebooks/
```

### Architecture modulaire

- **Services découplés** : Chaque service (récupération, génération, etc.) est indépendant
- **Configuration centralisée** : Un seul point de configuration pour toute l'application
- **Cache intelligent** : Mise en cache des résultats pour améliorer les performances
- **Extensibilité** : Architecture prête pour l'ajout de nouveaux providers LLM

## Licence

MIT License