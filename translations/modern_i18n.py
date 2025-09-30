"""
Module moderne d'internationalisation pour Streamlit
Utilise une approche hybride avec gettext et fallback
"""
import streamlit as st
from pathlib import Path
import json
import locale
from typing import Dict, Optional, Any
import importlib

class ModernI18N:
    """Gestionnaire d'internationalisation moderne"""

    def __init__(self):
        self.current_lang = "fr"  # langue par défaut
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        """Charge toutes les traductions disponibles"""
        translations_dir = Path(__file__).parent

        # Langues disponibles
        languages = ['fr', 'en']

        for lang in languages:
            try:
                # Essayer d'importer le module de traduction
                lang_module = importlib.import_module(f"translations.{lang}")
                self.translations[lang] = getattr(lang_module, "translations", {})
            except (ImportError, AttributeError) as e:
                print(f"Erreur lors du chargement de {lang}: {e}")
                self.translations[lang] = {}

    def set_language(self, lang_code: str):
        """Change la langue active"""
        if lang_code in self.translations:
            self.current_lang = lang_code
            # Stocker dans la session Streamlit
            st.session_state.language = lang_code

    def get_language(self) -> str:
        """Récupère la langue active"""
        # Priorité : session state > instance > défaut
        if hasattr(st.session_state, 'language'):
            self.current_lang = st.session_state.language
        return self.current_lang

    def t(self, key: str, *args, **kwargs) -> str:
        """
        Fonction de traduction principale (alias _)

        Args:
            key: Clé de traduction
            *args: Arguments pour formatage positionnel
            **kwargs: Arguments pour formatage nommé

        Returns:
            Texte traduit ou clé si non trouvé
        """
        current_lang = self.get_language()

        # Récupérer la traduction
        text = self.translations.get(current_lang, {}).get(key, key)

        # Fallback vers le français si la clé n'existe pas dans la langue courante
        if text == key and current_lang != 'fr':
            text = self.translations.get('fr', {}).get(key, key)

        # Formatage des arguments
        try:
            if args:
                return text.format(*args)
            elif kwargs:
                return text.format(**kwargs)
            else:
                return text
        except Exception as e:
            print(f"Erreur de formatage pour '{key}': {e}")
            return text

    def _(self, key: str, *args, **kwargs) -> str:
        """Alias pour t() - fonction de traduction courte"""
        return self.t(key, *args, **kwargs)

    def get_available_languages(self) -> Dict[str, str]:
        """Retourne les langues disponibles avec leurs noms"""
        return {
            'fr': 'Français',
            'en': 'English'
        }

    def add_language_selector(self, key: str = "language_selector"):
        """
        Ajoute un sélecteur de langue à la sidebar

        Args:
            key: Clé unique pour le widget
        """
        available_langs = self.get_available_languages()
        current_lang = self.get_language()

        # Créer le sélecteur
        new_lang = st.selectbox(
            self.t("language"),
            options=list(available_langs.keys()),
            format_func=lambda x: available_langs[x],
            index=list(available_langs.keys()).index(current_lang),
            key=key
        )

        # Si la langue change, mettre à jour
        if new_lang != current_lang:
            self.set_language(new_lang)
            st.rerun()  # Redémarrer l'app pour appliquer les changements


# Instance globale
_i18n = ModernI18N()

# Fonctions d'accès global
def init_i18n() -> ModernI18N:
    """Initialise et retourne l'instance d'internationalisation"""
    return _i18n

def t(key: str, *args, **kwargs) -> str:
    """Fonction globale de traduction"""
    return _i18n.t(key, *args, **kwargs)

def _(key: str, *args, **kwargs) -> str:
    """Fonction globale de traduction (alias court)"""
    return _i18n._(key, *args, **kwargs)

def set_language(lang_code: str):
    """Change la langue globalement"""
    _i18n.set_language(lang_code)

def get_language() -> str:
    """Récupère la langue active"""
    return _i18n.get_language()

def add_language_selector(key: str = "language_selector"):
    """Ajoute un sélecteur de langue"""
    _i18n.add_language_selector(key)


# Pour la compatibilité avec l'ancien système
def get_text(key: str, lang_code: str, *args) -> str:
    """Fonction de compatibilité avec l'ancien système"""
    old_lang = _i18n.get_language()
    _i18n.set_language(lang_code)
    result = _i18n.t(key, *args)
    _i18n.set_language(old_lang)
    return result