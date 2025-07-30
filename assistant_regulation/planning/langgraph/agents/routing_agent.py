"""
Routing Agent for LangGraph Workflow
===================================

Agent de routage qui utilise les services de routage existants pour
déterminer la stratégie optimale de recherche et traitement.
"""

import time
from typing import Dict, Any
from ..state.regulation_state import RegulationState
from assistant_regulation.planning.services.intelligent_routing_service import IntelligentRoutingService
from assistant_regulation.planning.services.knowledge_routing_service import KnowledgeRoutingService


class RoutingAgent:
    """
    Agent de routage qui affine les décisions de routage du superviseur.
    
    Utilise les services existants :
    - IntelligentRoutingService pour le routage intelligent
    - KnowledgeRoutingService pour le routage par domaine de connaissance
    """
    
    def __init__(self, 
                 intelligent_routing_service: IntelligentRoutingService,
                 knowledge_routing_service: KnowledgeRoutingService):
        """
        Initialise l'agent de routage avec les services existants.
        
        Args:
            intelligent_routing_service: Service de routage intelligent
            knowledge_routing_service: Service de routage par domaine
        """
        self.intelligent_routing_service = intelligent_routing_service
        self.knowledge_routing_service = knowledge_routing_service
        
    def __call__(self, state: RegulationState) -> RegulationState:
        """
        Point d'entrée principal de l'agent de routage.
        
        Args:
            state: État partagé du workflow
            
        Returns:
            État mis à jour avec les décisions de routage affinées
        """
        start_time = time.time()
        state["agent_trace"].append("routing_start")
        
        try:
            # 1. Routage intelligent basé sur l'analyse
            intelligent_routing = self._apply_intelligent_routing(state)
            
            # 2. Routage par domaine de connaissance
            knowledge_routing = self._apply_knowledge_routing(state)
            
            # 3. Fusionner les décisions de routage
            final_routing = self._merge_routing_decisions(
                state, intelligent_routing, knowledge_routing
            )
            
            # 4. Mettre à jour l'état avec les décisions finales
            state["routing_decision"].update(final_routing)
            
            state["agent_trace"].append("routing_complete")
            
        except Exception as e:
            state["error"] = f"Routing error: {str(e)}"
            state["agent_trace"].append("routing_error")
            
        finally:
            processing_time = time.time() - start_time
            state["processing_time"] += processing_time
            
        return state
    
    def _apply_intelligent_routing(self, state: RegulationState) -> Dict[str, Any]:
        """
        Applique le routage intelligent basé sur l'analyse de la requête.
        
        Args:
            state: État contenant l'analyse de requête
            
        Returns:
            Décisions de routage intelligent
        """
        query = state["query"]
        query_analysis = state.get("query_analysis", {})
        conversation_context = state.get("conversation_context", "")
        
        # Utiliser le service de routage intelligent existant
        routing_result = self.intelligent_routing_service.route_with_context(
            query=query,
            analysis=query_analysis,
            conversation_context=conversation_context
        )
        
        return {
            "intelligent_strategy": routing_result.get("strategy", "default"),
            "confidence": routing_result.get("confidence", 0.5),
            "recommended_sources": routing_result.get("sources", ["text", "images", "tables"]),
            "search_parameters": routing_result.get("parameters", {})
        }
    
    def _apply_knowledge_routing(self, state: RegulationState) -> Dict[str, Any]:
        """
        Applique le routage par domaine de connaissance.
        
        Args:
            state: État contenant l'analyse de requête
            
        Returns:
            Décisions de routage par domaine
        """
        query = state["query"]
        query_analysis = state.get("query_analysis", {})
        
        # Utiliser le service de routage par domaine existant
        domain_routing = self.knowledge_routing_service.route_by_domain(
            query=query,
            analysis=query_analysis
        )
        
        return {
            "domain": domain_routing.get("domain", "general"),
            "specialized_retrieval": domain_routing.get("specialized_retrieval", False),
            "domain_specific_parameters": domain_routing.get("parameters", {}),
            "priority_sources": domain_routing.get("priority_sources", [])
        }
    
    def _merge_routing_decisions(self, 
                                state: RegulationState,
                                intelligent_routing: Dict[str, Any],
                                knowledge_routing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fusionne les différentes décisions de routage en une stratégie cohérente.
        
        Args:
            state: État actuel
            intelligent_routing: Résultats du routage intelligent
            knowledge_routing: Résultats du routage par domaine
            
        Returns:
            Décisions de routage fusionnées
        """
        current_routing = state.get("routing_decision", {})
        
        # Fusionner les stratégies
        merged_routing = {
            "final_strategy": self._select_best_strategy(
                intelligent_routing.get("intelligent_strategy"),
                current_routing.get("strategy")
            ),
            "confidence_score": intelligent_routing.get("confidence", 0.5),
            "domain": knowledge_routing.get("domain", "general"),
            
            # Sources à utiliser (priorité au routage intelligent)
            "sources_to_use": self._merge_source_decisions(
                intelligent_routing.get("recommended_sources", []),
                knowledge_routing.get("priority_sources", []),
                state
            ),
            
            # Paramètres de recherche fusionnés
            "search_config": self._merge_search_parameters(
                intelligent_routing.get("search_parameters", {}),
                knowledge_routing.get("domain_specific_parameters", {}),
                state
            ),
            
            # Métadonnées pour debug
            "routing_details": {
                "intelligent_routing": intelligent_routing,
                "knowledge_routing": knowledge_routing,
                "merge_timestamp": time.time()
            }
        }
        
        return merged_routing
    
    def _select_best_strategy(self, intelligent_strategy: str, base_strategy: str) -> str:
        """
        Sélectionne la meilleure stratégie entre les options disponibles.
        
        Args:
            intelligent_strategy: Stratégie du routage intelligent
            base_strategy: Stratégie de base du superviseur
            
        Returns:
            Stratégie finale sélectionnée
        """
        # Priorité au routage intelligent s'il existe
        if intelligent_strategy and intelligent_strategy != "default":
            return intelligent_strategy
        return base_strategy or "default"
    
    def _merge_source_decisions(self, 
                               intelligent_sources: list,
                               priority_sources: list,
                               state: RegulationState) -> Dict[str, bool]:
        """
        Fusionne les décisions sur les sources à utiliser.
        
        Args:
            intelligent_sources: Sources recommandées par le routage intelligent
            priority_sources: Sources prioritaires par domaine
            state: État actuel avec préférences utilisateur
            
        Returns:
            Configuration finale des sources
        """
        # Préférences utilisateur
        user_wants_images = state.get("use_images", True)
        user_wants_tables = state.get("use_tables", True)
        
        # Fusionner les recommandations
        recommended_sources = set(intelligent_sources + priority_sources)
        
        return {
            "text": True,  # Toujours utiliser le texte
            "images": user_wants_images and ("images" in recommended_sources or len(recommended_sources) == 0),
            "tables": user_wants_tables and ("tables" in recommended_sources or len(recommended_sources) == 0)
        }
    
    def _merge_search_parameters(self, 
                                intelligent_params: Dict[str, Any],
                                domain_params: Dict[str, Any],
                                state: RegulationState) -> Dict[str, Any]:
        """
        Fusionne les paramètres de recherche des différents services.
        
        Args:
            intelligent_params: Paramètres du routage intelligent
            domain_params: Paramètres du routage par domaine
            state: État actuel
            
        Returns:
            Paramètres de recherche fusionnés
        """
        # Paramètres de base
        base_params = {
            "top_k": state.get("top_k", 5),
            "use_reranking": True,
            "similarity_threshold": 0.7
        }
        
        # Fusionner dans l'ordre de priorité
        merged_params = {**base_params}
        merged_params.update(domain_params)
        merged_params.update(intelligent_params)
        
        return merged_params