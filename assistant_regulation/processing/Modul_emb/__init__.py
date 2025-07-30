# Module de récupération optimisé - Version nettoyée
from .BaseRetriever import BaseRetriever
from .TextRetriever import SimpleTextRetriever
from .ImageRetriever import ImageRetriever
from .TableRetriever import TableRetriever

__all__ = [
    # Classes de base pour retrieval
    'BaseRetriever',
    'SimpleTextRetriever', 
    'ImageRetriever',
    'TableRetriever'
]

__version__ = "3.0.0-clean"
