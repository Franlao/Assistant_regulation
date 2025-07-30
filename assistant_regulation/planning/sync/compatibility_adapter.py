"""
Compatibility Adapter - Gère la rétrocompatibilité avec SimpleOrchestrator
"""

from typing import Dict
from assistant_regulation.planning.services import GenerationService, MemoryService


class CompatibilityAdapter:
    """Adapter pour maintenir la compatibilité avec SimpleOrchestrator."""
    
    def __init__(self, generation_service: GenerationService, memory_service: MemoryService):
        self.generation_service = generation_service
        self.memory_service = memory_service

    def get_conversation_stats(self) -> Dict:
        """Retourne des statistiques sur la conversation actuelle."""
        if not self.memory_service:
            return {"conversation_memory": "disabled"}
        
        # Sécurisation de l'accès à l'historique
        conversation_history = self.memory_service.conversation_history or []
        
        return {
            "conversation_memory": "enabled",
            "total_turns": len(conversation_history),
            "memory_tokens": sum(len(turn.get("content", "")) for turn in conversation_history if isinstance(turn, dict)),
            "window_size": getattr(self.memory_service, 'window_size', 10)
        }
    
    def clear_conversation_memory(self):
        """Vide la mémoire conversationnelle."""
        if self.memory_service:
            self.memory_service.clear_history()
    
    @property
    def conversation_memory(self):
        """Accès direct au service de mémoire pour compatibilité."""
        return self.memory_service
    
    @property 
    def llm_provider(self) -> str:
        """Provider LLM pour compatibilité."""
        return getattr(self.generation_service, 'llm_provider', "ollama")
    
    @llm_provider.setter
    def llm_provider(self, value: str):
        """Setter pour llm_provider pour compatibilité."""
        # Pour la compatibilité, on ne fait rien car le service est défini à l'initialisation
        pass
    
    @property
    def model_name(self) -> str:
        """Nom du modèle pour compatibilité.""" 
        return getattr(self.generation_service, 'model_name', "llama3.2")
    
    @model_name.setter
    def model_name(self, value: str):
        """Setter pour model_name pour compatibilité."""
        # Pour la compatibilité, on ne fait rien car le service est défini à l'initialisation
        pass 