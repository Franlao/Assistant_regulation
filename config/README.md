# Configuration Package 📁

Ce dossier contient tous les fichiers de configuration de l'Assistant Réglementaire Automobile.

## 📂 Structure

```
config/
├── __init__.py                 # Package Python avec exports
├── config.py                   # Module principal de configuration
├── config.json                 # Fichier de configuration persistant
├── CONFIG_GUIDE.md            # Guide d'utilisation complet
├── CONFIGURATION_SUMMARY.md   # Résumé de l'implémentation
└── README.md                  # Ce fichier
```

## 🚀 Utilisation

### Import Simple
```python
from config import get_config, save_config

# Obtenir la configuration
config = get_config()
print(f"App: {config.app_name} v{config.version}")

# Sauvegarder les modifications
save_config()
```

### Import Spécifique
```python
from config import get_llm_config, get_memory_config, get_rag_config

# Configurations par module
llm_config = get_llm_config()
memory_config = get_memory_config()
rag_config = get_rag_config()
```

### Import Complet
```python
from config import (
    AppConfig,
    get_config,
    reload_config,
    save_config
)
```

## 📄 Fichiers

### `config.py`
Module principal contenant :
- **Dataclasses** : 7 modules de configuration
- **Singleton** : Instance globale
- **Validation** : Vérification automatique
- **Persistence** : Sauvegarde/chargement JSON

### `config.json`
Fichier de configuration persistant :
- **Génération automatique** : Créé si inexistant
- **Structure hiérarchique** : Organisation par modules
- **Éditable** : Modification directe possible

### `CONFIG_GUIDE.md`
Documentation complète :
- **Guide d'utilisation** : Instructions détaillées
- **Exemples** : Snippets de code
- **Bonnes pratiques** : Recommandations
- **Dépannage** : Solutions aux problèmes

### `CONFIGURATION_SUMMARY.md`
Résumé de l'implémentation :
- **Architecture** : Vue d'ensemble du système
- **Fonctionnalités** : Liste des capacités
- **Avantages** : Bénéfices obtenus

## 🔧 Configuration par Défaut

Le système utilise des valeurs par défaut sensées :

```json
{
  "app_name": "Assistant Réglementaire Automobile",
  "version": "2.0.0",
  "llm": {
    "default_provider": "ollama",
    "default_ollama_model": "llama3.2"
  },
  "memory": {
    "enabled": true,
    "window_size": 7
  },
  "rag": {
    "enable_verification": true,
    "confidence_threshold": 0.7
  }
}
```

## 🌍 Variables d'Environnement

Support des variables d'environnement avec fallback :

```bash
export LLM_PROVIDER=mistral
export MEMORY_ENABLED=true
export CONFIDENCE_THRESHOLD=0.8
```

## 📝 Modification

### Via Interface Streamlit
1. Modifier les paramètres dans la sidebar
2. Cliquer "💾 Sauvegarder Config"
3. Les modifications sont persistées dans `config.json`

### Via Fichier JSON
1. Éditer directement `config/config.json`
2. Redémarrer l'application ou cliquer "🔄 Recharger Config"

### Via Code
```python
from config import get_config, save_config

config = get_config()
config.llm.default_provider = "mistral"
config.memory.window_size = 10
save_config()
```

## ✅ Avantages de cette Organisation

- **🗂️ Organisation claire** : Tous les fichiers de config dans un dossier
- **📦 Package Python** : Import facile avec `from config import ...`
- **📚 Documentation centralisée** : Guides et résumés dans le même endroit
- **🔄 Maintenance simplifiée** : Modifications localisées
- **🚀 Extensibilité** : Ajout facile de nouveaux modules

Cette organisation garantit une gestion propre et professionnelle de la configuration ! 