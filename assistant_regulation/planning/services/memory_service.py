from __future__ import annotations

import uuid
from typing import Dict, Any, Optional

from assistant_regulation.planning.sync.conversation_memory import ConversationMemory


class MemoryService:
    """Service en charge de la mémoire conversationnelle."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        *,
        llm_client: Optional[Dict] = None,
        model_name: str = "llama3.2",
        window_size: int = 7,
        max_turns_before_summary: int = 10,
    ) -> None:
        # Génère un ID de session si rien n'est fourni pour faciliter les tests
        if not session_id:
            session_id = str(uuid.uuid4())[:8]

        self._conversation_memory = ConversationMemory(
            session_id=session_id,
            window_size=window_size,
            max_turns_before_summary=max_turns_before_summary,
            llm_client=llm_client,
            model_name=model_name,
        )

    # ------------------------------------------------------------------
    def add_turn(self, user_query: str, assistant_response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._conversation_memory.add_turn(user_query, assistant_response, metadata)

    def get_context(self, user_query: str) -> str:
        return self._conversation_memory.get_context_for_query(user_query)

    # Pour debug / observabilité
    def stats(self) -> Dict[str, Any]:
        return self._conversation_memory.get_conversation_stats()
    
    def clear_history(self):
        """Vide l'historique de conversation."""
        if hasattr(self._conversation_memory, 'clear'):
            self._conversation_memory.clear()
        else:
            # Fallback - recréer une nouvelle instance
            self._conversation_memory.conversation_history = []
    
    @property
    def conversation_history(self):
        """Retourne l'historique de conversation."""
        return getattr(self._conversation_memory, 'conversation_history', [])
    
    @property 
    def window_size(self):
        """Retourne la taille de fenêtre."""
        return getattr(self._conversation_memory, 'window_size', 10)
    
    @window_size.setter
    def window_size(self, value: int):
        """Définit la taille de fenêtre."""
        if hasattr(self._conversation_memory, 'window_size'):
            self._conversation_memory.window_size = value 