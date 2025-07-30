"""
LangGraph Implementation for Assistant Regulation
================================================

Architecture multi-agent utilisant LangGraph pour orchestrer
les services existants de l'assistant réglementaire.

Structure:
- agents/: Agents LangGraph wrappant les services existants
- workflows/: Définitions des graphes de workflow
- state/: États partagés entre agents
- orchestrator.py: Orchestrateur principal LangGraph
"""

from .orchestrator import LangGraphOrchestrator
from .state.regulation_state import RegulationState

__all__ = [
    "LangGraphOrchestrator",
    "RegulationState"
]

__version__ = "1.0.0"