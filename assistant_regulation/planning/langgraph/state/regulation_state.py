"""
État partagé pour les workflows de régulation
============================================

Définit l'état TypedDict utilisé par tous les agents LangGraph
pour maintenir la cohérence des données entre les étapes.
"""

from typing import TypedDict, Dict, List, Any, Optional
from typing_extensions import NotRequired


class RegulationState(TypedDict):
    """
    État partagé pour le workflow de traitement des requêtes réglementaires.
    
    Cet état est passé entre tous les agents et maintient toutes les informations
    nécessaires au traitement complet d'une requête utilisateur.
    """
    
    # Requête utilisateur et contexte
    query: str
    conversation_context: NotRequired[str]
    use_images: NotRequired[bool]
    use_tables: NotRequired[bool]
    top_k: NotRequired[int]
    use_conversation_context: NotRequired[bool]
    use_advanced_routing: NotRequired[bool]
    
    # Analyse de la requête
    query_analysis: NotRequired[Dict[str, Any]]
    
    # Décisions de routage
    routing_decision: NotRequired[Dict[str, Any]]
    execution_plan: NotRequired[Dict[str, Any]]
    
    # Résultats de recherche
    retrieval_results: NotRequired[Dict[str, Any]]
    raw_chunks: NotRequired[Dict[str, List[Dict]]]
    
    # Résultats de validation
    validation_results: NotRequired[Dict[str, Any]]
    verified_chunks: NotRequired[Dict[str, List[Dict]]]
    
    # Construction du contexte
    context: NotRequired[str]
    combined_context: NotRequired[str]
    
    # Génération de réponse
    generation_results: NotRequired[Dict[str, Any]]
    answer: NotRequired[str]
    
    # Réponse finale
    final_response: NotRequired[Dict[str, Any]]
    
    # Métadonnées et debug
    agent_trace: NotRequired[List[str]]
    processing_time: NotRequired[float]
    error: NotRequired[str]
    
    # Sources et médias pour la réponse finale
    sources: NotRequired[List[Dict[str, Any]]]
    images: NotRequired[List[Dict[str, Any]]]
    tables: NotRequired[List[Dict[str, Any]]]