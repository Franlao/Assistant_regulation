"""
Module de gestion des traductions pour l'application
"""
from typing import Dict, Any, Optional
import importlib

# Langues disponibles
AVAILABLE_LANGUAGES = ["fr", "en"]
DEFAULT_LANGUAGE = "fr"

# Cache des traductions chargées
_loaded_translations: Dict[str, Dict[str, str]] = {}


def load_translations(lang_code: str) -> Dict[str, str]:
    """
    Charge les traductions pour la langue spécifiée
    
    Args:
        lang_code: Code de la langue à charger (fr, en, etc.)
        
    Returns:
        Dictionnaire des traductions
    """
    if lang_code not in AVAILABLE_LANGUAGES:
        lang_code = DEFAULT_LANGUAGE
    
    # Vérifier si les traductions sont déjà en cache
    if lang_code in _loaded_translations:
        return _loaded_translations[lang_code]
    
    try:
        # Importer dynamiquement le module de langue
        lang_module = importlib.import_module(f"translations.{lang_code}")
        translations = getattr(lang_module, "translations", {})
        _loaded_translations[lang_code] = translations
        return translations
    except (ImportError, AttributeError) as e:
        print(f"Erreur lors du chargement des traductions pour {lang_code}: {e}")
        # Fallback sur le français
        if lang_code != DEFAULT_LANGUAGE:
            return load_translations(DEFAULT_LANGUAGE)
        return {}


def get_text(key: str, lang_code: str, *args: Any) -> str:
    """
    Obtient une chaîne traduite avec placeholders optionnels
    
    Args:
        key: Clé de traduction à rechercher
        lang_code: Code de la langue
        *args: Arguments de formatage pour les placeholders
        
    Returns:
        Chaîne traduite (ou la clé si non trouvée)
    """
    translations = load_translations(lang_code)
    text = translations.get(key, key)
    
    if args:
        try:
            return text.format(*args)
        except Exception as e:
            print(f"Erreur de formatage pour la clé '{key}': {e}")
            return text
    return text 