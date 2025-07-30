# Guide Configuration Centralisée 🔧

## Vue d'ensemble

Le système de configuration centralisé permet de gérer tous les paramètres de l'Assistant Réglementaire Automobile depuis un seul endroit. La configuration est organisée en modules logiques et peut être modifiée via l'interface Streamlit ou directement dans le fichier `config.json`.

## Structure de Configuration

### 📁 Modules de Configuration

```python
AppConfig
├── llm: LLMConfig                    # Configuration des modèles de langage
├── memory: ConversationMemoryConfig  # Configuration mémoire conversationnelle  
├── rag: RAGConfig                   # Configuration système RAG
├── ui: UIConfig                     # Configuration interface utilisateur
├── database: DatabaseConfig         # Configuration bases de données
├── logging: LoggingConfig           # Configuration logs
└── security: SecurityConfig        # Configuration sécurité
```

## Modules Détaillés

### 🤖 LLMConfig - Modèles de Langage

```python
@dataclass
class LLMConfig:
    available_providers: ["ollama", "mistral"]
    default_provider: "ollama"
    
    # Modèles disponibles
    ollama_models: ["llama3.2", "mistral", "llama3.2:1b", "granite3.1-moe:3b"]
    mistral_models: ["mistral-medium", "mistral-small", "mistral-large-latest", "open-mixtral-8x7b"]
    
    # Modèles par défaut
    default_ollama_model: "llama3.2"
    default_mistral_model: "mistral-medium"
    
    # Paramètres génération
    temperature: 0.3
    max_tokens: 1024
    timeout: 300
```

**Usage:**
- Ajouter de nouveaux providers dans `available_providers`
- Ajouter de nouveaux modèles dans les listes correspondantes
- Modifier les paramètres de génération selon les besoins

### 🧠 ConversationMemoryConfig - Mémoire Conversationnelle

```python
@dataclass
class ConversationMemoryConfig:
    enabled: True                    # Activer/désactiver la mémoire
    window_size: 7                   # Tours récents en mémoire active
    max_turns_before_summary: 10     # Tours avant résumé automatique
    summary_max_words: 70            # Taille max des résumés
    memory_dir: ".conversation_memory" # Répertoire de stockage
    session_timeout_hours: 24        # Expiration des sessions
```

**Recommandations:**
- `window_size`: 5-10 pour un bon équilibre performance/contexte
- `max_turns_before_summary`: >= `window_size` + 3
- `summary_max_words`: 50-100 mots pour des résumés efficaces

### 🔍 RAGConfig - Système RAG

```python
@dataclass
class RAGConfig:
    enable_verification: True        # Vérification LLM des résultats
    use_images: True                # Inclure les images
    use_tables: True                # Inclure les tableaux
    default_top_k: 10               # Nombre de résultats par défaut
    
    # Seuils de confiance
    confidence_threshold: 0.7        # Seuil pour déclencher RAG
    force_rag_keywords: [            # Mots-clés forçant RAG
        "R046", "R107", "ECE", 
        "réglementation automobile", "norme", "directive"
    ]
    
    # Cache
    use_joblib_cache: True
    cache_dir: "./joblib_cache"
```

**Optimisation:**
- `confidence_threshold`: 0.6-0.8 selon la précision souhaitée
- Ajouter des mots-clés spécifiques à votre domaine
- Cache recommandé pour améliorer les performances

### 🎨 UIConfig - Interface Utilisateur

```python
@dataclass
class UIConfig:
    available_languages: ["fr", "en"]
    default_language: "fr"
    
    available_themes: ["light", "dark"]
    default_theme: "light"
    
    # Tailles d'images
    image_sizes: {
        "small": 150,
        "medium": 250, 
        "large": 350
    }
    
    max_sources_display: 50
    max_images_per_response: 10
```

## Utilisation

### 🚀 Accès Rapide

```python
from config import get_config, get_llm_config, get_memory_config

# Configuration complète
config = get_config()

# Configurations spécifiques
llm_config = get_llm_config()
memory_config = get_memory_config()
rag_config = get_rag_config()
ui_config = get_ui_config()
```

### 💾 Sauvegarde et Chargement

```python
from config import save_config, reload_config

# Modifier la configuration
config = get_config()
config.llm.default_provider = "mistral"
config.memory.window_size = 10

# Sauvegarder
save_config()

# Recharger depuis le fichier
reload_config()
```

### 🔧 Variables d'Environnement

Le système supporte les variables d'environnement avec fallback :

```bash
# Exemples de variables d'environnement
export LLM_PROVIDER=mistral
export MEMORY_ENABLED=true
export CONFIDENCE_THRESHOLD=0.8
export CACHE_DIR=/custom/cache
```

```python
from config import get_env_or_config

# Utilisation avec fallback
provider = get_env_or_config("LLM_PROVIDER", config.llm.default_provider)
```

## Interface Streamlit

### ⚙️ Gestion Configuration

L'interface Streamlit inclut une section "⚙️ Gestion Configuration" dans la sidebar :

- **Affichage** : Configuration actuelle
- **💾 Sauvegarder Config** : Persiste les modifications
- **🔄 Recharger Config** : Recharge depuis le fichier

### 🔄 Synchronisation Automatique

Les modifications dans l'interface sont automatiquement synchronisées :

1. **Modification UI** → `st.session_state.settings`
2. **Clic "Sauvegarder"** → Mise à jour `config` → `config.json`
3. **Redémarrage app** → Chargement depuis `config.json`

## Fichier config.json

### 📄 Structure

```json
{
  "app_name": "Assistant Réglementaire Automobile",
  "version": "2.0.0",
  "llm": {
    "available_providers": ["ollama", "mistral"],
    "default_provider": "ollama",
    "ollama_models": ["llama3.2", "mistral", "llama3.2:1b"],
    "temperature": 0.3
  },
  "memory": {
    "enabled": true,
    "window_size": 7,
    "max_turns_before_summary": 10
  },
  "rag": {
    "enable_verification": true,
    "confidence_threshold": 0.7,
    "force_rag_keywords": ["R046", "R107", "ECE"]
  }
}
```

### 🔄 Gestion Automatique

- **Création automatique** : Si `config.json` n'existe pas, création avec valeurs par défaut
- **Validation** : Vérification des valeurs lors du chargement
- **Migration** : Ajout automatique des nouveaux paramètres

## Bonnes Pratiques

### ✅ Recommandations

1. **Sauvegarde régulière** : Utilisez le bouton "💾 Sauvegarder Config" après modifications
2. **Test des modifications** : Testez en mode développement avant production
3. **Backup config.json** : Sauvegardez le fichier avant modifications importantes
4. **Variables d'environnement** : Utilisez pour les déploiements multi-environnements

### ⚠️ Précautions

1. **Validation automatique** : Le système valide les valeurs (ex: `confidence_threshold` entre 0-1)
2. **Redémarrage requis** : Certaines modifications nécessitent un redémarrage de l'app
3. **Permissions** : Assurez-vous que l'app peut écrire dans le répertoire

## Dépannage

### 🔍 Problèmes Courants

**Configuration non sauvegardée :**
```python
# Vérifier les permissions d'écriture
import os
print(os.access(".", os.W_OK))

# Forcer la sauvegarde
from config import save_config
save_config()
```

**Valeurs par défaut non appliquées :**
```python
# Supprimer config.json pour régénérer
import os
if os.path.exists("config.json"):
    os.remove("config.json")

# Recharger
from config import reload_config
reload_config()
```

**Erreurs de validation :**
```python
# Vérifier les contraintes
config = get_config()
print(f"Confidence: {config.rag.confidence_threshold}")  # Doit être 0-1
print(f"Window size: {config.memory.window_size}")       # Doit être >= 1
```

## Extension

### 🔧 Ajouter une Nouvelle Configuration

1. **Créer le dataclass :**
```python
@dataclass
class NewModuleConfig:
    param1: str = "default_value"
    param2: int = 42
```

2. **Ajouter à AppConfig :**
```python
@dataclass
class AppConfig:
    # ... existing configs ...
    new_module: NewModuleConfig = field(default_factory=NewModuleConfig)
```

3. **Créer fonction d'accès :**
```python
def get_new_module_config() -> NewModuleConfig:
    return get_config().new_module
```

4. **Utiliser dans l'application :**
```python
from config import get_new_module_config
new_config = get_new_module_config()
```

## Conclusion

Le système de configuration centralisé offre :

- ✅ **Centralisation** : Tous les paramètres en un seul endroit
- ✅ **Flexibilité** : Modification via UI ou fichier JSON
- ✅ **Validation** : Vérification automatique des valeurs
- ✅ **Persistence** : Sauvegarde automatique des modifications
- ✅ **Extensibilité** : Ajout facile de nouveaux modules

Cette approche garantit une gestion cohérente et maintenable de la configuration de l'Assistant Réglementaire Automobile. 