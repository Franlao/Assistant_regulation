"""
Retrieval Agent for LangGraph Workflow
=====================================

Agent de récupération qui utilise les services existants pour
effectuer la recherche multimodale dans les sources de données.
"""

import time
from typing import Dict, Any
from ..state.regulation_state import RegulationState
from assistant_regulation.planning.services.retrieval_service import RetrievalService
from assistant_regulation.planning.services.context_builder_service import ContextBuilderService
from assistant_regulation.planning.services.reranker_service import RerankerService


class RetrievalAgent:
    """
    Agent de récupération qui coordonne la recherche multimodale.
    
    Utilise les services existants :
    - RetrievalService pour la recherche dans les sources
    - ContextBuilderService pour construire le contexte
    - RerankerService pour le reranking des résultats
    """
    
    def __init__(self, 
                 retrieval_service: RetrievalService,
                 context_builder_service: ContextBuilderService,
                 reranker_service: RerankerService):
        """
        Initialise l'agent de récupération avec les services existants.
        
        Args:
            retrieval_service: Service de récupération multimodale
            context_builder_service: Service de construction de contexte
            reranker_service: Service de reranking
        """
        self.retrieval_service = retrieval_service
        self.context_builder_service = context_builder_service
        self.reranker_service = reranker_service
        
    def __call__(self, state: RegulationState) -> RegulationState:
        """
        Point d'entrée principal de l'agent de récupération.
        
        Args:
            state: État partagé du workflow
            
        Returns:
            État mis à jour avec les résultats de recherche
        """
        start_time = time.time()
        state["agent_trace"].append("retrieval_start")
        
        try:
            # 1. Effectuer la recherche multimodale
            raw_results = self._perform_multimodal_search(state)
            state["raw_chunks"] = raw_results
            
            # 2. Appliquer le reranking si configuré
            reranked_results = self._apply_reranking(state, raw_results)
            state["retrieval_results"] = reranked_results
            
            # 3. Construire le contexte préliminaire
            context = self._build_context(state, reranked_results)
            state["context"] = context
            
            state["agent_trace"].append("retrieval_complete")
            
        except Exception as e:
            state["error"] = f"Retrieval error: {str(e)}"
            state["agent_trace"].append("retrieval_error")
            
        finally:
            processing_time = time.time() - start_time
            state["processing_time"] += processing_time
            
        return state
    
    def _perform_multimodal_search(self, state: RegulationState) -> Dict[str, Any]:
        """
        Effectue la recherche multimodale en utilisant le service existant.
        
        Args:
            state: État contenant les paramètres de recherche
            
        Returns:
            Résultats bruts de la recherche
        """
        query = state["query"]
        routing_decision = state.get("routing_decision", {})
        conversation_context = state.get("conversation_context", "")
        
        # Extraire les paramètres de recherche
        search_config = routing_decision.get("search_config", {})
        sources_config = routing_decision.get("sources_to_use", {})
        
        # Paramètres pour le service de récupération
        search_params = {
            "query": query,
            "conversation_context": conversation_context,
            "use_images": sources_config.get("images", state.get("use_images", True)),
            "use_tables": sources_config.get("tables", state.get("use_tables", True)),
            "top_k": search_config.get("top_k", state.get("top_k", 5)),
            "similarity_threshold": search_config.get("similarity_threshold", 0.7),
            "domain": routing_decision.get("domain", "general")
        }
        
        # Utiliser le service de récupération existant
        results = self.retrieval_service.search_multimodal(**search_params)
        
        return results
    
    def _apply_reranking(self, state: RegulationState, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique le reranking aux résultats de recherche.
        
        Args:
            state: État actuel
            raw_results: Résultats bruts de la recherche
            
        Returns:
            Résultats après reranking
        """
        query = state["query"]
        routing_decision = state.get("routing_decision", {})
        search_config = routing_decision.get("search_config", {})
        
        # Vérifier si le reranking est activé
        if not search_config.get("use_reranking", True):
            return raw_results
        
        try:
            # Appliquer le reranking via le service existant
            reranked_results = self.reranker_service.rerank_results(
                query=query,
                results=raw_results,
                top_k=search_config.get("top_k", state.get("top_k", 5))
            )
            
            return reranked_results
            
        except Exception as e:
            # En cas d'erreur, retourner les résultats originaux
            state["agent_trace"].append(f"reranking_failed: {str(e)}")
            return raw_results
    
    def _build_context(self, state: RegulationState, retrieval_results: Dict[str, Any]) -> str:
        """
        Construit le contexte à partir des résultats de recherche.
        
        Args:
            state: État actuel
            retrieval_results: Résultats de la recherche
            
        Returns:
            Contexte construit pour la génération
        """
        query = state["query"]
        conversation_context = state.get("conversation_context", "")
        
        # Utiliser le service de construction de contexte existant
        context = self.context_builder_service.build_context(
            query=query,
            retrieval_results=retrieval_results,
            conversation_context=conversation_context,
            include_sources=True
        )
        
        return context
    
    def get_search_statistics(self, state: RegulationState) -> Dict[str, Any]:
        """
        Génère des statistiques sur la recherche effectuée.
        
        Args:
            state: État contenant les résultats de recherche
            
        Returns:
            Statistiques de recherche
        """
        retrieval_results = state.get("retrieval_results", {})
        
        stats = {
            "total_chunks_found": 0,
            "sources_used": [],
            "search_quality_score": 0.0
        }
        
        # Compter les chunks par source
        for source_type, chunks in retrieval_results.items():
            if isinstance(chunks, list):
                stats["total_chunks_found"] += len(chunks)
                if chunks:
                    stats["sources_used"].append(source_type)
        
        # Calculer un score de qualité basé sur la diversité des sources
        if stats["sources_used"]:
            stats["search_quality_score"] = len(stats["sources_used"]) / 3.0  # max 3 sources
        
        return stats