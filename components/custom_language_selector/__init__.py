"""
Composant personnalisé pour sélecteur de langue avec icônes Icons8
"""
import streamlit.components.v1 as components
import os

# Créer le composant personnalisé
_RELEASE = True

if not _RELEASE:
    # Mode développement - utilise un serveur local
    _component_func = components.declare_component(
        "language_selector",
        url="http://localhost:3001",
    )
else:
    # Mode production - utilise les fichiers locaux
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/build")
    _component_func = components.declare_component(
        "language_selector", path=build_dir
    )


def language_selector(current_language="fr", key=None):
    """
    Crée un sélecteur de langue personnalisé avec icônes Icons8

    Parameters:
    -----------
    current_language : str
        Langue actuelle ('fr' ou 'en')
    key : str
        Clé unique pour le composant

    Returns:
    --------
    str
        La langue sélectionnée ('fr' ou 'en')
    """
    component_value = _component_func(
        current_language=current_language,
        key=key,
        default=current_language
    )

    return component_value if component_value is not None else current_language