"""
Regulation Workflow for LangGraph
=================================

Définit le workflow principal pour le traitement des requêtes réglementaires
en utilisant une architecture multi-agent coordonnée.
"""

from typing import Dict, Any

# Import correct pour LangGraph 0.5.4+ (Pattern 2024)
try:
    from langgraph.graph import StateGraph, START, END
    LANGGRAPH_AVAILABLE = True
    print("[OK] LangGraph 0.5.4+ detecte - mode natif active")
except ImportError:
    try:
        # Fallback pour versions très anciennes
        from langgraph import StateGraph, START, END
        LANGGRAPH_AVAILABLE = True
        print("[OK] LangGraph legacy detecte - mode natif active")
    except ImportError:
        # Mode simulation si LangGraph indisponible
        class StateGraph:
            def __init__(self, state_schema):
                self.state_schema = state_schema
                # Mode simulation silencieux
            def add_node(self, name, func): pass
            def add_edge(self, from_node, to_node): pass
            def add_conditional_edges(self, from_node, condition, mapping): pass
            def set_entry_point(self, node): pass
            def compile(self): return self
            def invoke(self, state): return state
        
        START = "__start__"
        END = "__end__"
        LANGGRAPH_AVAILABLE = False
from ..state.regulation_state import RegulationState
from ..agents import (
    SupervisorAgent,
    RoutingAgent, 
    RetrievalAgent,
    ValidationAgent,
    GenerationAgent
)


def create_regulation_workflow(
    supervisor_agent: SupervisorAgent,
    routing_agent: RoutingAgent,
    retrieval_agent: RetrievalAgent,
    validation_agent: ValidationAgent,
    generation_agent: GenerationAgent
):
    """
    Crée le workflow principal pour le traitement des requêtes réglementaires.
    
    Args:
        supervisor_agent: Agent superviseur
        routing_agent: Agent de routage
        retrieval_agent: Agent de récupération
        validation_agent: Agent de validation
        generation_agent: Agent de génération
        
    Returns:
        Workflow LangGraph compilé
    """
    
    # Créer le graphe d'état
    workflow = StateGraph(RegulationState)
    
    # Ajouter les agents comme nœuds (seulement s'ils existent)
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("routing", routing_agent)
    workflow.add_node("retrieval", retrieval_agent)
    
    # Validation optionnelle
    if validation_agent is not None:
        workflow.add_node("validation", validation_agent)
    
    workflow.add_node("generation", generation_agent)
    
    # Définir le workflow (SIMPLIFIÉ POUR COMPATIBILITÉ)
    if LANGGRAPH_AVAILABLE:
        # Mode LangGraph véritable - workflow linéaire simple
        workflow.add_edge(START, "supervisor")
        workflow.add_edge("supervisor", "routing")
        workflow.add_edge("routing", "retrieval")
        
        if validation_agent:
            workflow.add_edge("retrieval", "validation")
            workflow.add_edge("validation", "generation")
        else:
            workflow.add_edge("retrieval", "generation")
        
        workflow.add_edge("generation", END)
    else:
        # Mode simulation - pas besoin d'edges
        pass
    
    # Compiler le workflow
    return workflow.compile()


def _route_after_supervisor(state: RegulationState) -> str:
    """
    Détermine le prochain nœud après le superviseur.
    
    Args:
        state: État actuel du workflow
        
    Returns:
        Nom du prochain nœud à exécuter
    """
    # Vérifier s'il y a une erreur critique
    if state.get("error"):
        return "end"
    
    # Vérifier les résultats de l'analyse
    query_analysis = state.get("query_analysis", {})
    execution_plan = state.get("execution_plan", {})
    
    # Si la requête ne nécessite pas de RAG, aller directement à generation
    if not query_analysis.get("needs_rag", True):
        return "generation"
    
    # Vérifier le plan d'exécution pour le prochain agent
    next_agent = execution_plan.get("next_agent", "routing")
    
    if next_agent == "generation":
        return "generation"
    else:
        return "routing"


def create_simple_workflow(
    supervisor_agent: SupervisorAgent,
    generation_agent: GenerationAgent
):
    """
    Crée un workflow simplifié pour les requêtes ne nécessitant pas de RAG.
    
    Args:
        supervisor_agent: Agent superviseur
        generation_agent: Agent de génération
        
    Returns:
        Workflow simplifié compilé
    """
    workflow = StateGraph(RegulationState)
    
    # Ajouter seulement les agents essentiels
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("generation", generation_agent)
    
    # Flux simple
    workflow.add_edge(START, "supervisor")
    workflow.add_edge("supervisor", "generation")
    workflow.add_edge("generation", END)
    
    return workflow.compile()


def create_debug_workflow(
    supervisor_agent: SupervisorAgent,
    routing_agent: RoutingAgent,
    retrieval_agent: RetrievalAgent,
    validation_agent: ValidationAgent,
    generation_agent: GenerationAgent
):
    """
    Crée un workflow avec debug détaillé pour le développement.
    
    Args:
        supervisor_agent: Agent superviseur
        routing_agent: Agent de routage
        retrieval_agent: Agent de récupération 
        validation_agent: Agent de validation
        generation_agent: Agent de génération
        
    Returns:
        Workflow avec debug compilé
    """
    workflow = StateGraph(RegulationState)
    
    # Wrapper les agents avec debug
    debug_supervisor = _create_debug_wrapper(supervisor_agent, "SUPERVISOR")
    debug_routing = _create_debug_wrapper(routing_agent, "ROUTING")
    debug_retrieval = _create_debug_wrapper(retrieval_agent, "RETRIEVAL")
    debug_validation = _create_debug_wrapper(validation_agent, "VALIDATION")
    debug_generation = _create_debug_wrapper(generation_agent, "GENERATION")
    
    # Ajouter les agents wrappés
    workflow.add_node("supervisor", debug_supervisor)
    workflow.add_node("routing", debug_routing)
    workflow.add_node("retrieval", debug_retrieval)
    workflow.add_node("validation", debug_validation)
    workflow.add_node("generation", debug_generation)
    
    # Même structure que le workflow principal
    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            "routing": "routing",
            "generation": "generation",
            "end": END
        }
    )
    
    workflow.add_edge("routing", "retrieval")
    workflow.add_edge("retrieval", "validation")
    workflow.add_edge("validation", "generation")
    workflow.add_edge("generation", END)
    
    return workflow.compile()


def _create_debug_wrapper(agent, agent_name: str):
    """
    Crée un wrapper de debug pour un agent.
    
    Args:
        agent: Agent à wrapper
        agent_name: Nom de l'agent pour le debug
        
    Returns:
        Agent wrappé avec debug
    """
    def debug_agent(state: RegulationState) -> RegulationState:
        print(f"\\n=== {agent_name} START ===")
        print(f"Current state keys: {list(state.keys())}")
        
        # Exécuter l'agent original
        result_state = agent(state)
        
        print(f"=== {agent_name} END ===")
        print(f"Updated state keys: {list(result_state.keys())}")
        if "error" in result_state:
            print(f"ERROR: {result_state['error']}")
        print(f"Agent trace: {result_state.get('agent_trace', [])}")
        print()
        
        return result_state
    
    return debug_agent


# Configurations prédéfinies de workflow
WORKFLOW_CONFIGS = {
    "full": {
        "description": "Workflow complet avec tous les agents",
        "agents": ["supervisor", "routing", "retrieval", "validation", "generation"],
        "factory": create_regulation_workflow
    },
    
    "simple": {
        "description": "Workflow simplifié sans RAG",
        "agents": ["supervisor", "generation"],
        "factory": create_simple_workflow
    },
    
    "debug": {
        "description": "Workflow avec debug détaillé",
        "agents": ["supervisor", "routing", "retrieval", "validation", "generation"],
        "factory": create_debug_workflow
    },
    
    "no_validation": {
        "description": "Workflow sans validation pour les requêtes simples",
        "agents": ["supervisor", "routing", "retrieval", "generation"],
        "factory": None  # À implémenter si nécessaire
    }
}


def get_workflow_config(config_name: str) -> Dict[str, Any]:
    """
    Récupère une configuration de workflow prédéfinie.
    
    Args:
        config_name: Nom de la configuration
        
    Returns:
        Configuration du workflow
    """
    return WORKFLOW_CONFIGS.get(config_name, WORKFLOW_CONFIGS["full"])


def list_available_workflows() -> list:
    """
    Liste les workflows disponibles.
    
    Returns:
        Liste des noms de workflow disponibles
    """
    return list(WORKFLOW_CONFIGS.keys())