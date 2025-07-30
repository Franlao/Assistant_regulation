# API Assistant Réglementaire Automobile

Cette API permet d'interroger une base de connaissances sur les réglementations automobiles en utilisant un système RAG (Retrieval-Augmented Generation). Elle permet de poser des questions en langage naturel et d'obtenir des réponses précises basées sur les documents réglementaires.

## Fonctionnalités

- **Requêtes en langage naturel** : Posez des questions sur les réglementations et obtenez des réponses précises
- **Multimodal** : Récupération d'informations depuis le texte, les images et les tableaux
- **Vérification LLM** : Option pour vérifier la pertinence des résultats avant génération
- **Gestion de documents** : Upload et indexation de nouveaux documents réglementaires
- **Documentation OpenAPI** : Documentation complète des endpoints disponibles

## Architecture

Le système est basé sur une architecture RAG (Retrieval-Augmented Generation) :

1. **Indexation** : Les documents PDF sont analysés et divisés en chunks (texte, images, tableaux)
2. **Recherche** : Les chunks pertinents sont récupérés grâce à une recherche vectorielle
3. **Vérification** : Un modèle LLM vérifie la pertinence des résultats (optionnel)
4. **Génération** : Un modèle LLM génère une réponse en utilisant uniquement les informations récupérées
5. **API REST** : Exposition des fonctionnalités via une API REST

## Prérequis

- Python 3.10+
- Ollama ou une clé API Mistral AI
- Espace disque pour la base de données vectorielle

## Installation

1. Cloner le dépôt :
   ```bash
   git clone <repo_url>
   cd assistant-reglementaire-api
   ```

2. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Configurer l'environnement (optionnel) :
   ```bash
   cp .env.example .env
   # Modifier les valeurs dans .env selon vos besoins
   ```

4. Initialiser la base de données :
   ```bash
   python db_init.py --dir ./Data
   ```

## Démarrage

### Démarrage en développement

```bash
uvicorn api:app --reload
```

### Démarrage en production

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Avec Docker

```bash
docker build -t assistant-reglementaire-api .
docker run -p 8000:8000 assistant-reglementaire-api
```

## Utilisation

### Documentation de l'API

- Swagger UI : http://localhost:8000/docs
- ReDoc : http://localhost:8000/redoc

### Exemples d'utilisation

#### Requête simple

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quelles sont les exigences pour les rétroviseurs de Classe III?",
    "use_images": true,
    "use_tables": true
  }'
```

#### Configuration de l'orchestrateur

```bash
curl -X POST "http://localhost:8000/configure" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_provider": "mistral",
    "model_name": "mistral-medium",
    "enable_verification": true
  }'
```

#### Upload d'un nouveau document

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/chemin/vers/R046.pdf"
```

## Structure du projet

```
assistant-reglementaire-api/
├── api.py                   # Point d'entrée de l'API
├── config.py                # Configuration de l'application
├── db_init.py               # Script d'initialisation de la base de données
├── Dockerfile               # Configuration Docker
├── requirements.txt         # Dépendances Python
├── routes/                  # Routes de l'API
│   └── upload.py            # Routes pour la gestion des documents
├── src/                     # Code source existant
│   ├── Processing_pattern/  # Modules de traitement
│   └── Planning_pattern/    # Orchestrateur principal
└── Data/                    # Répertoire pour les documents PDF
```

## Licence

[Licence MIT]

# Alternatives à Streamlit pour les interfaces de chatbot multiagent

Ce dépôt contient des exemples de code pour implémenter un chatbot multiagent capable de générer du texte, des tableaux et des images, en utilisant différentes alternatives à Streamlit.

## Contexte

Streamlit est pratique pour le prototypage rapide, mais présente des limitations en termes de personnalisation esthétique et de flexibilité. Ce projet explore des alternatives offrant une meilleure expérience utilisateur et davantage d'options de personnalisation.

## Alternatives proposées

### 1. Gradio

**Exemple** : `gradio_app.py`

**Avantages** :
- Plus moderne et élégant que Streamlit par défaut
- Personnalisation CSS plus facile
- Optimisé pour les interfaces IA (chat, images, tableaux)
- Documentation claire et nombreux exemples
- Bonne communauté et maintenance régulière

**Inconvénients** :
- Moins d'options de mise en page complexe que des frameworks frontend complets
- Pas aussi complet pour les visualisations de données que Dash

**Installation** :
```bash
pip install gradio
```

### 2. Chainlit

**Exemple** : `chainlit_app.py`

**Avantages** :
- Spécialement conçu pour les applications LLM et les chatbots
- Interface de chat moderne et esthétique par défaut
- Support natif pour la gestion des messages, images, tableaux
- Fonctionnalités avancées (feedback, évaluations, étapes)
- Gestion des sessions utilisateurs intégrée

**Inconvénients** :
- Relativement récent, donc communauté plus petite
- Options de personnalisation légèrement plus limitées que des frameworks web

**Installation** :
```bash
pip install chainlit
```

### 3. Flask + React (ou Vue, Angular)

**Exemple** : `flask_react_example/`

**Avantages** :
- Personnalisation complète et illimitée
- Séparation claire backend/frontend
- Interface utilisateur moderne avec des bibliothèques comme Material-UI
- Possibilité d'utiliser des bibliothèques de visualisation avancées
- Évolutivité pour des applications complexes

**Inconvénients** :
- Courbe d'apprentissage plus élevée
- Nécessite des compétences en développement web
- Configuration initiale plus longue
- Déploiement légèrement plus complexe

**Installation** :
```bash
# Backend
pip install flask flask-cors

# Frontend (avec create-react-app)
npx create-react-app frontend
cd frontend
npm install @mui/material @mui/icons-material @emotion/react @emotion/styled @mui/x-data-grid axios
```

### 4. Dash/Plotly

**Non inclus dans les exemples, mais mentionné comme alternative**

**Avantages** :
- Excellent pour les visualisations de données complexes
- Basé sur React mais utilisable en Python
- Composants interactifs avancés
- Bonne documentation et support

**Inconvénients** :
- Moins optimisé pour les interfaces de chat
- Peut nécessiter plus de code personnalisé pour des interfaces de chatbot

## Comparaison

| Critère | Streamlit | Gradio | Chainlit | Flask + React |
|---------|-----------|--------|----------|--------------|
| Facilité d'utilisation | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★☆☆☆ |
| Personnalisation | ★★☆☆☆ | ★★★★☆ | ★★★★☆ | ★★★★★ |
| Esthétique par défaut | ★★☆☆☆ | ★★★★☆ | ★★★★★ | ★★★★★ |
| Support chatbot | ★★★☆☆ | ★★★★☆ | ★★★★★ | ★★★★★ |
| Support multimédia | ★★★☆☆ | ★★★★☆ | ★★★★☆ | ★★★★★ |
| Complexité de mise en place | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★☆☆☆ |
| Évolutivité | ★★☆☆☆ | ★★★☆☆ | ★★★☆☆ | ★★★★★ |

## Comment utiliser ce dépôt

Chaque dossier ou fichier contient un exemple d'implémentation pour la technologie correspondante :

1. **Gradio** : Exécutez `python gradio_app.py`
2. **Chainlit** : Exécutez `chainlit run chainlit_app.py`
3. **Flask + React** : 
   - Backend : `cd flask_react_example && python app.py`
   - Frontend : `cd flask_react_example/frontend && npm start`

## Conclusion

Le choix de l'interface dépend de vos besoins spécifiques :

- **Gradio** est un excellent compromis entre facilité d'utilisation et personnalisation
- **Chainlit** est parfait pour les applications de chat basées sur LLM avec des fonctionnalités prêtes à l'emploi
- **Flask + React** offre une personnalisation illimitée pour les projets plus ambitieux nécessitant une interface utilisateur sophistiquée

Pour la plupart des chatbots multiagents, **Chainlit** et **Gradio** sont recommandés pour leur équilibre entre facilité de développement et qualité visuelle.