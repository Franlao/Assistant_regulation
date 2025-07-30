"""
Validation Agent for LangGraph Workflow
======================================

Agent de validation qui utilise les services existants pour
vérifier et valider les chunks récupérés.
"""

import time
from typing import Dict, Any
from ..state.regulation_state import RegulationState
from assistant_regulation.planning.services.validation_service import ValidationService


class ValidationAgent:
    """
    Agent de validation qui vérifie la pertinence des chunks récupérés.
    
    Utilise les services existants :
    - ValidationService pour la validation des chunks
    """
    
    def __init__(self, validation_service: ValidationService):
        """
        Initialise l'agent de validation avec le service existant.
        
        Args:
            validation_service: Service de validation des chunks
        """
        self.validation_service = validation_service
        
    def __call__(self, state: RegulationState) -> RegulationState:
        """
        Point d'entrée principal de l'agent de validation.
        
        Args:
            state: État partagé du workflow
            
        Returns:
            État mis à jour avec les résultats de validation
        """
        start_time = time.time()
        state["agent_trace"].append("validation_start")
        
        try:
            # Vérifier si la validation est nécessaire
            if not self._should_validate(state):
                # Passer directement les résultats sans validation
                state["verified_chunks"] = state.get("retrieval_results", {})
                state["validation_results"] = {"skipped": True, "reason": "validation_disabled"}
                state["agent_trace"].append("validation_skipped")
                return state
            
            # 1. Valider les chunks récupérés
            validation_results = self._validate_chunks(state)
            state["validation_results"] = validation_results
            
            # 2. Filtrer les chunks validés
            verified_chunks = self._filter_validated_chunks(state, validation_results)
            state["verified_chunks"] = verified_chunks
            
            # 3. Mettre à jour le contexte avec les chunks validés
            updated_context = self._update_context_with_validation(state)
            state["combined_context"] = updated_context
            
            state["agent_trace"].append("validation_complete")
            
        except Exception as e:
            # En cas d'erreur, utiliser les résultats sans validation
            state["error"] = f"Validation error: {str(e)}"
            state["verified_chunks"] = state.get("retrieval_results", {})
            state["validation_results"] = {"error": str(e)}
            state["agent_trace"].append("validation_error")
            
        finally:
            processing_time = time.time() - start_time
            state["processing_time"] += processing_time
            
        return state
    
    def _should_validate(self, state: RegulationState) -> bool:
        """
        Détermine si la validation doit être effectuée.
        
        Args:
            state: État actuel
            
        Returns:
            True si la validation doit être effectuée
        """
        # Vérifier si le service de validation est disponible
        if not self.validation_service:
            return False
        
        # Vérifier s'il y a des chunks à valider
        retrieval_results = state.get("retrieval_results", {})
        if not retrieval_results:
            return False
        
        # Vérifier la configuration de validation
        routing_decision = state.get("routing_decision", {})
        search_config = routing_decision.get("search_config", {})
        
        # Par défaut, valider si la complexité est élevée
        query_analysis = state.get("query_analysis", {})
        complexity = query_analysis.get("complexity", "medium")
        
        return search_config.get("enable_validation", complexity in ["high", "medium"])
    
    def _validate_chunks(self, state: RegulationState) -> Dict[str, Any]:
        """
        Valide les chunks récupérés en utilisant le service existant.
        
        Args:
            state: État contenant les chunks à valider
            
        Returns:
            Résultats de la validation
        """
        query = state["query"]
        retrieval_results = state.get("retrieval_results", {})
        conversation_context = state.get("conversation_context", "")
        
        # Paramètres de validation
        validation_params = {
            "query": query,
            "chunks": retrieval_results,
            "conversation_context": conversation_context,
            "validation_criteria": self._get_validation_criteria(state)
        }
        
        # Utiliser le service de validation existant
        validation_results = self.validation_service.validate_chunks(**validation_params)
        
        return validation_results
    
    def _get_validation_criteria(self, state: RegulationState) -> Dict[str, Any]:
        """
        Détermine les critères de validation basés sur l'analyse de la requête.
        
        Args:
            state: État actuel
            
        Returns:
            Critères de validation
        """
        query_analysis = state.get("query_analysis", {})
        routing_decision = state.get("routing_decision", {})
        
        criteria = {
            "relevance_threshold": 0.7,
            "semantic_similarity_threshold": 0.6,
            "domain_specific": routing_decision.get("domain", "general") != "general",
            "strict_mode": query_analysis.get("complexity", "medium") == "high"
        }
        
        # Ajuster les critères selon le domaine
        domain = routing_decision.get("domain", "general")
        if domain in ["safety", "legal", "technical"]:
            criteria["relevance_threshold"] = 0.8
            criteria["semantic_similarity_threshold"] = 0.7
            criteria["strict_mode"] = True
        
        return criteria
    
    def _filter_validated_chunks(self, 
                                state: RegulationState, 
                                validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtre les chunks basés sur les résultats de validation.
        
        Args:
            state: État actuel
            validation_results: Résultats de la validation
            
        Returns:
            Chunks filtrés et validés
        """
        retrieval_results = state.get("retrieval_results", {})
        
        if not validation_results or validation_results.get("error"):
            # En cas d'erreur de validation, retourner tous les chunks
            return retrieval_results
        
        filtered_chunks = {}
        
        # Filtrer chaque type de source
        for source_type, chunks in retrieval_results.items():
            if isinstance(chunks, list):
                source_validation = validation_results.get(source_type, {})
                valid_indices = source_validation.get("valid_chunks", list(range(len(chunks))))
                
                # Garder seulement les chunks validés
                filtered_chunks[source_type] = [
                    chunk for i, chunk in enumerate(chunks) 
                    if i in valid_indices
                ]
            else:
                # Pour les données non-list, garder tel quel
                filtered_chunks[source_type] = chunks
        
        return filtered_chunks
    
    def _update_context_with_validation(self, state: RegulationState) -> str:
        """
        Met à jour le contexte en utilisant les chunks validés.
        
        Args:
            state: État contenant les chunks validés
            
        Returns:
            Contexte mis à jour
        """
        # Si nous avons un service de construction de contexte, l'utiliser
        # Sinon, construire un contexte simple
        verified_chunks = state.get("verified_chunks", {})
        base_context = state.get("context", "")
        
        if not verified_chunks:
            return base_context
        
        # Construction simple du contexte avec chunks validés
        context_parts = []
        
        # Ajouter le contexte de base s'il existe
        if base_context:
            context_parts.append(base_context)
        
        # Ajouter des informations sur la validation
        validation_results = state.get("validation_results", {})
        if validation_results and not validation_results.get("skipped"):
            validation_summary = self._create_validation_summary(validation_results)
            context_parts.append(f"\\n\\n[Validation Summary: {validation_summary}]")
        
        return "\\n".join(context_parts)
    
    def _create_validation_summary(self, validation_results: Dict[str, Any]) -> str:
        """
        Crée un résumé des résultats de validation.
        
        Args:
            validation_results: Résultats de la validation
            
        Returns:
            Résumé textuel de la validation
        """
        summary_parts = []
        
        for source_type, source_validation in validation_results.items():
            if isinstance(source_validation, dict) and "valid_chunks" in source_validation:
                total_chunks = source_validation.get("total_chunks", 0)
                valid_chunks = len(source_validation.get("valid_chunks", []))
                
                if total_chunks > 0:
                    percentage = (valid_chunks / total_chunks) * 100
                    summary_parts.append(f"{source_type}: {valid_chunks}/{total_chunks} ({percentage:.1f}%)")
        
        return ", ".join(summary_parts) if summary_parts else "No validation performed"
    
    def get_validation_statistics(self, state: RegulationState) -> Dict[str, Any]:
        """
        Génère des statistiques détaillées sur la validation.
        
        Args:
            state: État contenant les résultats de validation
            
        Returns:
            Statistiques de validation
        """
        validation_results = state.get("validation_results", {})
        
        if validation_results.get("skipped"):
            return {"status": "skipped", "reason": validation_results.get("reason")}
        
        if validation_results.get("error"):
            return {"status": "error", "error": validation_results.get("error")}
        
        stats = {
            "status": "completed",
            "sources_validated": 0,
            "total_chunks_input": 0,
            "total_chunks_validated": 0,
            "validation_rate": 0.0,
            "quality_score": 0.0
        }
        
        for source_type, source_validation in validation_results.items():
            if isinstance(source_validation, dict):
                stats["sources_validated"] += 1
                total = source_validation.get("total_chunks", 0)
                valid = len(source_validation.get("valid_chunks", []))
                
                stats["total_chunks_input"] += total
                stats["total_chunks_validated"] += valid
        
        if stats["total_chunks_input"] > 0:
            stats["validation_rate"] = stats["total_chunks_validated"] / stats["total_chunks_input"]
            stats["quality_score"] = min(1.0, stats["validation_rate"] * 1.2)  # Bonus pour haute validation
        
        return stats