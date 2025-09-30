"""
Module de gestion des traductions pour l'application
Utilise le nouveau système moderne d'internationalisation
"""

# Import du nouveau système moderne
from .modern_i18n import (
    init_i18n,
    t, _,  # Fonctions de traduction
    set_language, get_language,
    add_language_selector,
    get_text  # Compatibilité ancien système
)

# Initialisation automatique
_i18n_instance = init_i18n()

# Export des fonctions principales pour compatibilité
__all__ = [
    't', '_', 'get_text',
    'set_language', 'get_language',
    'add_language_selector',
    'init_i18n'
]

# Langues disponibles (pour compatibilité)
AVAILABLE_LANGUAGES = ["fr", "en"]
DEFAULT_LANGUAGE = "fr" 