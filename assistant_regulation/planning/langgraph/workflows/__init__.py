"""
LangGraph Workflows for Assistant Regulation
===========================================

Définitions des workflows (graphes) pour orchestrer
les agents dans le traitement des requêtes réglementaires.
"""

from .regulation_workflow import create_regulation_workflow
from .streaming_workflow import create_streaming_workflow

__all__ = [
    "create_regulation_workflow",
    "create_streaming_workflow"
]