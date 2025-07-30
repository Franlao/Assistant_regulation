"""
Supervisor Agent for LangGraph Workflow
======================================

Agent superviseur qui coordonne le workflow en utilisant les services
de routage existants pour prendre des décisions d'orchestration.
"""

import time
from typing import Dict, List, Any
from ..state.regulation_state import RegulationState
from assistant_regulation.planning.services.master_routing_service import MasterRoutingService
from assistant_regulation.planning.agents.query_analysis_agent import QueryAnalysisAgent


class SupervisorAgent:
    """
    Agent superviseur qui analyse les requêtes et détermine le flow optimal.
    
    Utilise les services existants :
    - MasterRoutingService pour les décisions de routage
    - QueryAnalysisAgent pour l'analyse des requêtes
    """
    
    def __init__(self, 
                 master_routing_service: MasterRoutingService,
                 query_analysis_agent: QueryAnalysisAgent):
        """
        Initialise le superviseur avec les services de routage existants.
        
        Args:
            master_routing_service: Service de routage principal
            query_analysis_agent: Agent d'analyse de requêtes
        """
        self.master_routing_service = master_routing_service
        self.query_analysis_agent = query_analysis_agent
        
    def __call__(self, state: RegulationState) -> RegulationState:
        """
        Point d'entrée principal du superviseur.
        
        Args:
            state: État partagé du workflow
            
        Returns:
            État mis à jour avec les décisions de routage
        """
        start_time = time.time()
        
        # Initialiser la trace d'exécution
        if "agent_trace" not in state:
            state["agent_trace"] = []
        state["agent_trace"].append("supervisor_start")
        
        try:
            # 1. Analyser la requête
            query_analysis = self._analyze_query(state)
            state["query_analysis"] = query_analysis
            
            # 2. Déterminer la stratégie de routage
            routing_decision = self._determine_routing_strategy(state)
            state["routing_decision"] = routing_decision
            
            # 3. Créer le plan d'exécution
            execution_plan = self._create_execution_plan(state)
            state["execution_plan"] = execution_plan
            
            # 4. Configurer les paramètres par défaut si non fournis
            self._set_default_parameters(state)
            
            state["agent_trace"].append("supervisor_complete")
            
        except Exception as e:
            state["error"] = f"Supervisor error: {str(e)}"
            state["agent_trace"].append("supervisor_error")
            
        finally:
            # Enregistrer le temps de traitement
            processing_time = time.time() - start_time
            if "processing_time" not in state:
                state["processing_time"] = 0
            state["processing_time"] += processing_time
            
        return state
    
    def _analyze_query(self, state: RegulationState) -> Dict[str, Any]:
        """
        Analyse la requête utilisateur en utilisant l'agent d'analyse existant.
        
        Args:
            state: État contenant la requête
            
        Returns:
            Résultats de l'analyse de requête
        """
        query = state["query"]
        
        # Utiliser l'agent d'analyse existant
        analysis = self.query_analysis_agent.analyse_query(query)
        
        return analysis
    
    def _determine_routing_strategy(self, state: RegulationState) -> Dict[str, Any]:
        """
        Détermine la stratégie de routage en utilisant le service de routage.
        
        Args:
            state: État contenant l'analyse de requête
            
        Returns:
            Décision de routage
        """
        query = state["query"]
        query_analysis = state.get("query_analysis", {})
        
        # Utiliser le service de routage principal
        if state.get("use_advanced_routing", True):
            # Routage avancé avec analyse contextuell
            routing_decision = self.master_routing_service.route_query_advanced(
                query, 
                query_analysis
            )
        else:
            # Routage traditionnel
            routing_decision = self.master_routing_service.route_query_simple(query)
            
        return routing_decision
    
    def _create_execution_plan(self, state: RegulationState) -> Dict[str, Any]:
        """
        Crée un plan d'exécution détaillé basé sur les décisions de routage.
        
        Args:
            state: État contenant les décisions de routage
            
        Returns:
            Plan d'exécution pour les agents suivants
        """
        query = state["query"]
        routing_decision = state.get("routing_decision", {})
        query_analysis = state.get("query_analysis", {})
        
        # Obtenir le plan d'exécution du service de routage
        execution_plan = self.master_routing_service.get_execution_plan(query)
        
        # Enrichir avec les informations d'analyse
        execution_plan.update({
            "needs_rag": query_analysis.get("needs_rag", True),
            "complexity": query_analysis.get("complexity", "medium"),
            "domain": query_analysis.get("domain", "general"),
            "routing_strategy": routing_decision.get("strategy", "default"),
            "next_agent": self._determine_next_agent(routing_decision, query_analysis)
        })
        
        return execution_plan
    
    def _determine_next_agent(self, 
                             routing_decision: Dict[str, Any], 
                             query_analysis: Dict[str, Any]) -> str:
        """
        Détermine le prochain agent à exécuter.
        
        Args:
            routing_decision: Décision de routage
            query_analysis: Analyse de la requête
            
        Returns:
            Nom du prochain agent à exécuter
        """
        # Si la requête nécessite RAG, aller vers retrieval
        if query_analysis.get("needs_rag", True):
            return "routing"  # D'abord le routage détaillé, puis retrieval
        
        # Si pas de RAG nécessaire, aller directement à generation
        return "generation"
    
    def _set_default_parameters(self, state: RegulationState) -> None:
        """
        Configure les paramètres par défaut si non fournis.
        
        Args:
            state: État à configurer
        """
        # Paramètres par défaut
        defaults = {
            "use_images": True,
            "use_tables": True,
            "top_k": 5,
            "use_conversation_context": True,
            "use_advanced_routing": True
        }
        
        for key, default_value in defaults.items():
            if key not in state:
                state[key] = default_value
    
    def get_routing_explanation(self, state: RegulationState) -> str:
        """
        Génère une explication des décisions de routage prises.
        
        Args:
            state: État contenant les décisions
            
        Returns:
            Explication textuelle des décisions
        """
        query = state["query"]
        return self.master_routing_service.explain_routing_decision(query)