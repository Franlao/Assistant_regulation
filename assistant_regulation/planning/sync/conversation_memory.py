# src/Planning_pattern/sync/conversation_memory.py

import json
import os
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class ConversationTurn:
    """Représente un tour de conversation (question + réponse)"""
    user_query: str
    assistant_response: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour sérialisation"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Crée une instance depuis un dictionnaire"""
        return cls(**data)

@dataclass
class ConversationSummary:
    """Représente un résumé de conversation"""
    summary_text: str
    turns_count: int
    start_timestamp: float
    end_timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSummary':
        return cls(**data)

class ConversationMemory:
    """
    Gestionnaire de mémoire conversationnelle avec fenêtre glissante et résumé automatique.
    
    Fonctionnalités:
    - Maintient les 5-10 derniers échanges en contexte
    - Résume automatiquement les anciens échanges quand > 10 tours
    - Persiste la mémoire sur disque
    - Priorise le contexte selon l'ordre défini
    """
    
    def __init__(self, 
                 session_id: str,
                 window_size: int = 7,  # Nombre de tours à garder en mémoire active
                 max_turns_before_summary: int = 10,
                 memory_dir: str = ".conversation_memory",
                 llm_client: Optional[Dict] = None,
                 model_name: str = "llama3.2"):
        """
        Initialise la gestion de mémoire conversationnelle.
        
        Args:
            session_id: Identifiant unique de la session de conversation
            window_size: Nombre de tours récents à garder (5-10 recommandé)
            max_turns_before_summary: Nombre max de tours avant résumé automatique
            memory_dir: Répertoire de stockage de la mémoire
            llm_client: Client LLM pour générer les résumés
            model_name: Nom du modèle pour la génération de résumés
        """
        self.session_id = session_id
        self.window_size = window_size
        self.max_turns_before_summary = max_turns_before_summary
        self.memory_dir = memory_dir
        self.llm_client = llm_client
        self.model_name = model_name
        
        # Configuration du logging
        self.logger = logging.getLogger(__name__)
        
        # Structures de données
        self.recent_turns: List[ConversationTurn] = []
        self.summaries: List[ConversationSummary] = []
        
        # Créer le répertoire de mémoire
        os.makedirs(memory_dir, exist_ok=True)
        
        # Charger la mémoire existante
        self._load_memory()
    
    def add_turn(self, user_query: str, assistant_response: str, metadata: Optional[Dict] = None) -> None:
        """
        Ajoute un nouveau tour de conversation.
        
        Args:
            user_query: Question de l'utilisateur
            assistant_response: Réponse de l'assistant
            metadata: Métadonnées additionnelles (sources, confiance, etc.)
        """        
        # Créer le nouveau tour
        turn = ConversationTurn(
            user_query=user_query,
            assistant_response=assistant_response,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        # Ajouter à la mémoire récente
        self.recent_turns.append(turn)
        
        # Vérifier si un résumé est nécessaire
        if len(self.recent_turns) > self.max_turns_before_summary:
            self._create_summary_and_cleanup()
        
        # Sauvegarder sur disque
        self._save_memory()
        
        self.logger.info(f"Tour ajouté à la mémoire. Tours récents: {len(self.recent_turns)}, Résumés: {len(self.summaries)}")
    
    def get_context_for_query(self, current_query: str) -> str:
        """
        Construit le contexte conversationnel pour la requête courante.
        
        Ordre de priorité:
        1. Intention actuelle de l'utilisateur (current_query)
        2. Derniers échanges (fenêtre glissante)
        3. Résumé du contexte plus ancien
        
        Args:
            current_query: La requête courante de l'utilisateur
            
        Returns:
            Contexte formaté pour l'assistant
        """
        context_parts = []
        
        # 1. Résumés des anciens échanges (s'il y en a)
        if self.summaries:
            context_parts.append("=== CONTEXTE PRÉCÉDENT ===")
            for summary in self.summaries:
                context_parts.append(f"Résumé de {summary.turns_count} échanges précédents:")
                context_parts.append(summary.summary_text)
            context_parts.append("")
        
        # 2. Tours récents (fenêtre glissante)
        if self.recent_turns:
            context_parts.append("=== ÉCHANGES RÉCENTS ===")
            # Garder seulement les N derniers tours selon window_size
            recent_window = self.recent_turns[-self.window_size:]
            
            for i, turn in enumerate(recent_window, 1):
                context_parts.append(f"Échange {i}:")
                context_parts.append(f"Utilisateur: {turn.user_query}")
                response_preview = turn.assistant_response[:200]
                if len(turn.assistant_response) > 200:
                    response_preview += "..."
                context_parts.append(f"Assistant: {response_preview}")
                context_parts.append("")
        
        # 3. Requête actuelle
        context_parts.append("=== REQUÊTE ACTUELLE ===")
        context_parts.append(f"Utilisateur: {current_query}")
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur la conversation"""
        total_turns = len(self.recent_turns) + sum(s.turns_count for s in self.summaries)
        
        return {
            "session_id": self.session_id,
            "total_turns": total_turns,
            "recent_turns": len(self.recent_turns),
            "summaries_count": len(self.summaries),
            "window_size": self.window_size,
            "memory_usage": "active" if self.recent_turns or self.summaries else "empty"
        }
    
    def clear_memory(self) -> None:
        """Efface toute la mémoire de la session"""
        self.recent_turns.clear()
        self.summaries.clear()
        self._save_memory()
        self.logger.info(f"Mémoire effacée pour la session {self.session_id}")
    
    def _create_summary_and_cleanup(self) -> None:
        """Crée un résumé des anciens tours et nettoie la mémoire récente"""
        # Prendre les tours les plus anciens pour le résumé
        turns_to_summarize = self.recent_turns[:-self.window_size]
        
        if not turns_to_summarize:
            return
        
        # Générer le résumé
        summary_text = self._generate_summary(turns_to_summarize)
        
        # Créer l'objet résumé
        summary = ConversationSummary(
            summary_text=summary_text,
            turns_count=len(turns_to_summarize),
            start_timestamp=turns_to_summarize[0].timestamp,
            end_timestamp=turns_to_summarize[-1].timestamp
        )
        
        # Ajouter aux résumés
        self.summaries.append(summary)
        
        # Garder seulement les tours récents
        self.recent_turns = self.recent_turns[-self.window_size:]
        
        self.logger.info(f"Résumé créé pour {len(turns_to_summarize)} tours. Tours récents conservés: {len(self.recent_turns)}")
    
    def _generate_summary(self, turns: List[ConversationTurn]) -> str:
        """
        Génère un résumé des tours de conversation.
        
        Args:
            turns: Liste des tours à résumer
            
        Returns:
            Résumé en ≤ 70 mots
        """
        if not self.llm_client:
            # Fallback: résumé simple sans LLM
            topics = []
            for turn in turns:
                # Extraire quelques mots-clés de chaque question
                words = turn.user_query.lower().split()
                key_words = [w for w in words if len(w) > 4 and w not in ['dans', 'avec', 'pour', 'cette', 'comment', 'quelle', 'quels']]
                topics.extend(key_words[:2])
            
            unique_topics = list(set(topics))[:5]
            return f"Discussion sur: {', '.join(unique_topics)}. {len(turns)} échanges sur les réglementations automobiles."
        
        # Préparer le contenu pour le résumé LLM
        content = []
        for i, turn in enumerate(turns, 1):
            content.append(f"Q{i}: {turn.user_query}")
            content.append(f"R{i}: {turn.assistant_response[:150]}...")
        
        conversation_text = "\n".join(content)
        
        prompt = f"""
        Résumez cette conversation en maximum 70 mots, en français, en conservant les points clés et le contexte réglementaire:

        {conversation_text}

        Résumé (≤ 70 mots):
        """
        
        try:
            if self.llm_client['type'] == 'mistral':
                response = self.llm_client['client'].chat.complete(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=100
                )
                summary = response.choices[0].message.content.strip()
            elif self.llm_client['type'] == 'ollama':
                response = self.llm_client['client'].chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    options={'temperature': 0.3}
                )
                summary = response['message']['content'].strip()
            else:
                raise Exception("Type de client LLM non supporté")
            
            # Vérifier la limite de mots
            words = summary.split()
            if len(words) > 70:
                summary = " ".join(words[:70]) + "..."
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du résumé: {str(e)}")
            # Fallback en cas d'erreur
            return f"Résumé de {len(turns)} échanges sur les réglementations automobiles."
    
    def _get_memory_file_path(self) -> str:
        """Retourne le chemin du fichier de mémoire pour cette session"""
        return os.path.join(self.memory_dir, f"memory_{self.session_id}.json")
    
    def _save_memory(self) -> None:
        """Sauvegarde la mémoire sur disque"""
        try:
            memory_data = {
                "session_id": self.session_id,
                "recent_turns": [turn.to_dict() for turn in self.recent_turns],
                "summaries": [summary.to_dict() for summary in self.summaries],
                "last_updated": time.time()
            }
            
            with open(self._get_memory_file_path(), 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de la mémoire: {str(e)}")
    
    def _load_memory(self) -> None:
        """Charge la mémoire depuis le disque"""
        file_path = self._get_memory_file_path()
        
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)
            
            # Charger les tours récents
            self.recent_turns = [
                ConversationTurn.from_dict(turn_data) 
                for turn_data in memory_data.get("recent_turns", [])
            ]
            
            # Charger les résumés
            self.summaries = [
                ConversationSummary.from_dict(summary_data)
                for summary_data in memory_data.get("summaries", [])
            ]
            
            self.logger.info(f"Mémoire chargée: {len(self.recent_turns)} tours récents, {len(self.summaries)} résumés")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de la mémoire: {str(e)}")
            # En cas d'erreur, commencer avec une mémoire vide
            self.recent_turns = []
            self.summaries = []

    def export_conversation(self) -> Dict[str, Any]:
        """Exporte toute la conversation pour analyse ou backup"""
        return {
            "session_id": self.session_id,
            "export_timestamp": time.time(),
            "summaries": [s.to_dict() for s in self.summaries],
            "recent_turns": [t.to_dict() for t in self.recent_turns],
            "stats": self.get_conversation_stats()
        } 