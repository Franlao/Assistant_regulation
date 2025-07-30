"""
Streaming Workflow for LangGraph
================================

Workflow optimisé pour les réponses en streaming temps réel.
"""

from typing import Dict, Any, Generator

# Import compatible avec différentes versions de LangGraph
try:
    from langgraph import StateGraph, START, END
    from langgraph.graph import Graph
except ImportError:
    try:
        from langgraph.graph import StateGraph, START, END, Graph
    except ImportError:
        # Fallback pour versions très anciennes
        class StateGraph:
            def __init__(self, state_schema):
                self.state_schema = state_schema
                print("[WARNING] LangGraph non disponible - mode simulation")
            def add_node(self, name, func): pass
            def add_edge(self, from_node, to_node): pass
            def add_conditional_edges(self, from_node, condition, mapping): pass
            def compile(self): return self
        
        class Graph:
            def __init__(self): pass
        
        START = "START"
        END = "END"
from ..state.regulation_state import RegulationState
from ..agents import (
    SupervisorAgent,
    RoutingAgent,
    RetrievalAgent,
    ValidationAgent,
    GenerationAgent
)


def create_streaming_workflow(
    supervisor_agent: SupervisorAgent,
    routing_agent: RoutingAgent,
    retrieval_agent: RetrievalAgent,
    validation_agent: ValidationAgent,
    generation_agent: GenerationAgent
) -> Graph:
    """
    Crée un workflow optimisé pour le streaming.
    
    Le workflow streaming parallélise certaines opérations et commence
    la génération dès que possible pour réduire la latence.
    
    Args:
        supervisor_agent: Agent superviseur
        routing_agent: Agent de routage
        retrieval_agent: Agent de récupération
        validation_agent: Agent de validation
        generation_agent: Agent de génération
        
    Returns:
        Workflow streaming compilé
    """
    workflow = StateGraph(RegulationState)
    
    # Wrapper les agents pour le streaming
    streaming_supervisor = _create_streaming_wrapper(supervisor_agent, "supervisor")
    streaming_routing = _create_streaming_wrapper(routing_agent, "routing") 
    streaming_retrieval = _create_streaming_wrapper(retrieval_agent, "retrieval")
    streaming_validation = _create_streaming_wrapper(validation_agent, "validation")
    streaming_generation = _create_streaming_wrapper(generation_agent, "generation")
    
    # Ajouter les agents
    workflow.add_node("supervisor", streaming_supervisor)
    workflow.add_node("routing", streaming_routing)
    workflow.add_node("retrieval", streaming_retrieval)
    workflow.add_node("validation", streaming_validation)
    workflow.add_node("generation", streaming_generation)
    
    # Flow optimisé pour streaming
    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        _route_for_streaming,
        {
            "routing": "routing",
            "generation": "generation",
            "end": END
        }
    )
    
    workflow.add_edge("routing", "retrieval")
    
    # Validation conditionnelle pour accélérer le streaming
    workflow.add_conditional_edges(
        "retrieval",
        _decide_validation_for_streaming,
        {
            "validation": "validation",
            "generation": "generation"
        }
    )
    
    workflow.add_edge("validation", "generation")
    workflow.add_edge("generation", END)
    
    return workflow.compile()


def _create_streaming_wrapper(agent, agent_name: str):
    """
    Crée un wrapper streaming pour un agent.
    
    Args:
        agent: Agent à wrapper
        agent_name: Nom de l'agent
        
    Returns:
        Agent wrappé pour streaming
    """
    def streaming_agent(state: RegulationState) -> RegulationState:
        # Marquer le début du streaming pour cet agent
        if "streaming_events" not in state:
            state["streaming_events"] = []
        
        state["streaming_events"].append({
            "agent": agent_name,
            "status": "started",
            "timestamp": __import__("time").time()
        })
        
        # Exécuter l'agent avec optimisations streaming
        if agent_name == "generation":
            # Pour la génération, préparer le streaming
            state["stream_ready"] = True
        
        result_state = agent(state)
        
        state["streaming_events"].append({
            "agent": agent_name,
            "status": "completed",
            "timestamp": __import__("time").time()
        })
        
        return result_state
    
    return streaming_agent


def _route_for_streaming(state: RegulationState) -> str:
    """
    Routage optimisé pour le streaming.
    
    Args:
        state: État actuel
        
    Returns:
        Prochain nœud pour streaming optimal
    """
    # Pour le streaming, on veut minimiser la latence
    query_analysis = state.get("query_analysis", {})
    
    # Si requête simple, aller directement à generation
    if query_analysis.get("complexity", "medium") == "low":
        return "generation"
    
    # Sinon, passer par le routage
    if query_analysis.get("needs_rag", True):
        return "routing"
    
    return "generation"


def _decide_validation_for_streaming(state: RegulationState) -> str:
    """
    Décide si la validation est nécessaire pour le streaming.
    
    Args:
        state: État après retrieval
        
    Returns:
        "validation" ou "generation"
    """
    query_analysis = state.get("query_analysis", {})
    routing_decision = state.get("routing_decision", {})
    
    # Pour le streaming, éviter la validation si possible
    complexity = query_analysis.get("complexity", "medium")
    domain = routing_decision.get("domain", "general")
    
    # Validation obligatoire pour domaines critiques
    if domain in ["safety", "legal"] or complexity == "high":
        return "validation"
    
    # Sinon, aller directement à generation pour accélérer
    return "generation"


class StreamingWorkflowExecutor:
    """
    Exécuteur spécialisé pour les workflows streaming.
    """
    
    def __init__(self, workflow: Graph):
        """
        Initialise l'exécuteur streaming.
        
        Args:
            workflow: Workflow LangGraph compilé
        """
        self.workflow = workflow
    
    def execute_stream(self, initial_state: RegulationState) -> Generator[Dict[str, Any], None, None]:
        """
        Exécute le workflow en mode streaming.
        
        Args:
            initial_state: État initial
            
        Yields:
            Événements de streaming
        """
        # Initialiser le streaming
        yield {
            "type": "workflow_start",
            "message": "Démarrage du traitement...",
            "timestamp": __import__("time").time()
        }
        
        try:
            # Exécuter le workflow avec streaming
            final_state = None
            for step_result in self.workflow.stream(initial_state):
                # Yielder les événements intermédiaires
                for node_name, node_state in step_result.items():
                    yield {
                        "type": "agent_update",
                        "agent": node_name,
                        "state_keys": list(node_state.keys()),
                        "timestamp": __import__("time").time()
                    }
                    
                    # Si c'est l'agent de génération, commencer le streaming de réponse
                    if node_name == "generation" and node_state.get("stream_ready"):
                        generation_agent = self._get_generation_agent()
                        if hasattr(generation_agent, 'generate_streaming_response'):
                            yield {
                                "type": "generation_start",
                                "message": "Génération de la réponse...",
                                "timestamp": __import__("time").time()
                            }
                            
                            for chunk in generation_agent.generate_streaming_response(node_state):
                                yield {
                                    "type": "generation_chunk",
                                    "content": chunk,
                                    "timestamp": __import__("time").time()
                                }
                    
                    final_state = node_state
            
            # Yielder le résultat final
            if final_state:
                yield {
                    "type": "workflow_complete",
                    "final_response": final_state.get("final_response", {}),
                    "timestamp": __import__("time").time()
                }
                
        except Exception as e:
            yield {
                "type": "error",
                "message": f"Erreur pendant le streaming: {str(e)}",
                "timestamp": __import__("time").time()
            }
    
    def _get_generation_agent(self):
        """
        Récupère l'agent de génération du workflow.
        
        Returns:
            Agent de génération ou None
        """
        # Cette méthode devrait être implémentée pour récupérer
        # l'agent de génération du workflow compilé
        # Pour l'instant, retourner None
        return None


def create_fast_streaming_workflow(
    supervisor_agent: SupervisorAgent,
    generation_agent: GenerationAgent
) -> Graph:
    """
    Crée un workflow streaming ultra-rapide sans RAG.
    
    Args:
        supervisor_agent: Agent superviseur
        generation_agent: Agent de génération
        
    Returns:
        Workflow streaming rapide
    """
    workflow = StateGraph(RegulationState)
    
    # Agents optimisés pour vitesse maximale
    fast_supervisor = _create_fast_wrapper(supervisor_agent)
    fast_generation = _create_fast_wrapper(generation_agent)
    
    workflow.add_node("supervisor", fast_supervisor)
    workflow.add_node("generation", fast_generation)
    
    workflow.add_edge(START, "supervisor")
    workflow.add_edge("supervisor", "generation")
    workflow.add_edge("generation", END)
    
    return workflow.compile()


def _create_fast_wrapper(agent):
    """
    Crée un wrapper ultra-rapide pour un agent.
    
    Args:
        agent: Agent à wrapper
        
    Returns:
        Agent wrappé pour vitesse maximale
    """
    def fast_agent(state: RegulationState) -> RegulationState:
        # Désactiver certaines fonctionnalités pour la vitesse
        state["fast_mode"] = True
        
        # Exécuter l'agent
        result = agent(state)
        
        return result
    
    return fast_agent