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
        conversation_history = getattr(self.memory_service, 'conversation_history', []) or []
        
        # Calculer le nombre de tours récents et de résumés
        window_size = getattr(self.memory_service, 'window_size', 10)
        recent_turns = len(conversation_history[-window_size:]) if conversation_history else 0
        
        # Estimer le nombre de résumés (tours au-delà de la fenêtre)
        summaries_count = max(0, len(conversation_history) - window_size) if conversation_history else 0
        
        return {
            "conversation_memory": "enabled",
            "total_turns": len(conversation_history),
            "recent_turns": recent_turns,
            "summaries_count": summaries_count,
            "memory_tokens": sum(len(str(turn.get("content", ""))) for turn in conversation_history if isinstance(turn, dict)),
            "window_size": window_size
        }
    
    def clear_conversation_memory(self):
        """Vide la mémoire conversationnelle."""
        if self.memory_service:
            self.memory_service.clear_history()
    
    def export_conversation(self) -> Dict:
        """Exporte la conversation actuelle."""
        if not self.memory_service:
            return {"conversation_memory": "disabled", "history": []}
        
        # Exporter l'historique de conversation
        if hasattr(self.memory_service, 'export_conversation'):
            return self.memory_service.export_conversation()
        else:
            # Fallback simple
            conversation_history = getattr(self.memory_service, 'conversation_history', [])
            return {
                "conversation_memory": "enabled",
                "export_time": str(__import__('datetime').datetime.now()),
                "total_turns": len(conversation_history),
                "history": conversation_history
            }
    
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