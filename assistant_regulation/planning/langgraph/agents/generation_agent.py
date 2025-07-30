"""
Generation Agent for LangGraph Workflow
======================================

Agent de génération qui utilise les services existants pour
générer la réponse finale à partir du contexte validé.
"""

import time
from typing import Dict, Any, Generator
from ..state.regulation_state import RegulationState
from assistant_regulation.planning.services.generation_service import GenerationService
from assistant_regulation.planning.services.memory_service import MemoryService


class GenerationAgent:
    """
    Agent de génération qui produit la réponse finale.
    
    Utilise les services existants :
    - GenerationService pour la génération de réponse
    - MemoryService pour la gestion de mémoire conversationnelle
    """
    
    def __init__(self, 
                 generation_service: GenerationService,
                 memory_service: MemoryService):
        """
        Initialise l'agent de génération avec les services existants.
        
        Args:
            generation_service: Service de génération de réponse
            memory_service: Service de gestion de mémoire
        """
        self.generation_service = generation_service
        self.memory_service = memory_service
        
    def __call__(self, state: RegulationState) -> RegulationState:
        """
        Point d'entrée principal de l'agent de génération.
        
        Args:
            state: État partagé du workflow
            
        Returns:
            État mis à jour avec la réponse générée
        """
        start_time = time.time()
        state["agent_trace"].append("generation_start")
        
        try:
            # 1. Préparer les paramètres de génération
            generation_params = self._prepare_generation_parameters(state)
            
            # 2. Générer la réponse
            generation_result = self._generate_response(state, generation_params)
            state["generation_results"] = generation_result
            state["answer"] = generation_result.get("answer", "")
            
            # 3. Extraire les sources et médias pour la réponse finale
            sources_and_media = self._extract_sources_and_media(state)
            state.update(sources_and_media)
            
            # 4. Construire la réponse finale
            final_response = self._build_final_response(state)
            state["final_response"] = final_response
            
            # 5. Mettre à jour la mémoire conversationnelle
            self._update_conversation_memory(state)
            
            state["agent_trace"].append("generation_complete")
            
        except Exception as e:
            state["error"] = f"Generation error: {str(e)}"
            state["answer"] = f"Désolé, une erreur s'est produite lors de la génération de la réponse: {str(e)}"
            state["final_response"] = self._build_error_response(state, str(e))
            state["agent_trace"].append("generation_error")
            
        finally:
            processing_time = time.time() - start_time
            state["processing_time"] += processing_time
            
        return state
    
    def _prepare_generation_parameters(self, state: RegulationState) -> Dict[str, Any]:
        """
        Prépare les paramètres pour la génération de réponse.
        
        Args:
            state: État actuel
            
        Returns:
            Paramètres de génération
        """
        query = state["query"]
        context = state.get("combined_context") or state.get("context", "")
        conversation_context = state.get("conversation_context", "")
        
        # Analyse pour ajuster le style de génération
        query_analysis = state.get("query_analysis", {})
        routing_decision = state.get("routing_decision", {})
        
        params = {
            "query": query,
            "context": context,
            "conversation_context": conversation_context,
            "generation_style": self._determine_generation_style(query_analysis, routing_decision),
            "include_sources": True,
            "language": query_analysis.get("language", "fr"),
            "complexity_level": query_analysis.get("complexity", "medium"),
            "domain": routing_decision.get("domain", "general")
        }
        
        return params
    
    def _determine_generation_style(self, 
                                   query_analysis: Dict[str, Any], 
                                   routing_decision: Dict[str, Any]) -> str:
        """
        Détermine le style de génération approprié.
        
        Args:
            query_analysis: Analyse de la requête
            routing_decision: Décision de routage
            
        Returns:
            Style de génération à utiliser
        """
        domain = routing_decision.get("domain", "general")
        complexity = query_analysis.get("complexity", "medium")
        
        # Style selon le domaine
        if domain == "legal":
            return "formal_legal"
        elif domain == "technical":
            return "technical_detailed"
        elif domain == "safety":
            return "safety_focused"
        elif complexity == "high":
            return "comprehensive"
        elif complexity == "low":
            return "simple_concise"
        else:
            return "balanced"
    
    def _generate_response(self, state: RegulationState, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Génère la réponse en utilisant le service existant.
        
        Args:
            state: État actuel
            params: Paramètres de génération
            
        Returns:
            Résultat de la génération
        """
        # Utiliser generate_answer au lieu de generate_response (API correcte)
        answer = self.generation_service.generate_answer(
            query=params.get("query", ""),
            context=params.get("context", ""),
            conversation_context=params.get("conversation_context", ""),
            temperature=params.get("temperature", 0.3),
            max_tokens=params.get("max_tokens", 1024)
        )
        
        result = {
            "answer": answer,
            "success": True
        }
        
        # Ajouter des métadonnées sur la génération
        result["generation_metadata"] = {
            "style": params.get("generation_style", "balanced"),
            "language": params.get("language", "fr"),
            "domain": params.get("domain", "general"),
            "timestamp": time.time()
        }
        
        return result
    
    def _extract_sources_and_media(self, state: RegulationState) -> Dict[str, Any]:
        """
        Extrait les sources et médias pour la réponse finale.
        
        Args:
            state: État contenant les chunks validés
            
        Returns:
            Sources et médias extraits
        """
        verified_chunks = state.get("verified_chunks", {})
        
        sources = []
        images = []
        tables = []
        
        # Extraire les sources textuelles
        text_chunks = verified_chunks.get("text", [])
        if isinstance(text_chunks, list):
            for chunk in text_chunks:
                if isinstance(chunk, dict) and "source" in chunk:
                    source_info = {
                        "content": chunk.get("content", ""),
                        "source": chunk.get("source", ""),
                        "page": chunk.get("page", ""),
                        "regulation": chunk.get("regulation", ""),
                        "relevance_score": chunk.get("score", 0.0)
                    }
                    sources.append(source_info)
        
        # Extraire les images
        image_chunks = verified_chunks.get("images", [])
        if isinstance(image_chunks, list):
            for image in image_chunks:
                if isinstance(image, dict):
                    image_info = {
                        "path": image.get("path", ""),
                        "description": image.get("description", ""),
                        "source": image.get("source", ""),
                        "relevance_score": image.get("score", 0.0)
                    }
                    images.append(image_info)
        
        # Extraire les tableaux
        table_chunks = verified_chunks.get("tables", [])
        if isinstance(table_chunks, list):
            for table in table_chunks:
                if isinstance(table, dict):
                    table_info = {
                        "content": table.get("content", ""),
                        "structure": table.get("structure", {}),
                        "source": table.get("source", ""),
                        "relevance_score": table.get("score", 0.0)
                    }
                    tables.append(table_info)
        
        return {
            "sources": sources,
            "images": images,
            "tables": tables
        }
    
    def _build_final_response(self, state: RegulationState) -> Dict[str, Any]:
        """
        Construit la réponse finale au format attendu.
        
        Args:
            state: État complet avec tous les résultats
            
        Returns:
            Réponse finale formatée
        """
        query = state["query"]
        answer = state.get("answer", "")
        sources = state.get("sources", [])
        images = state.get("images", [])
        tables = state.get("tables", [])
        
        # Métadonnées sur le traitement
        processing_metadata = {
            "query_analysis": state.get("query_analysis", {}),
            "routing_decision": state.get("routing_decision", {}),
            "validation_performed": "validation_results" in state and not state.get("validation_results", {}).get("skipped"),
            "processing_time": state.get("processing_time", 0.0),
            "agent_trace": state.get("agent_trace", []),
            "sources_count": len(sources),
            "images_count": len(images),
            "tables_count": len(tables)
        }
        
        final_response = {
            "query": query,
            "answer": answer,
            "sources": sources,
            "images": images, 
            "tables": tables,
            "metadata": processing_metadata,
            "success": not bool(state.get("error")),
            "error": state.get("error")
        }
        
        return final_response
    
    def _build_error_response(self, state: RegulationState, error_message: str) -> Dict[str, Any]:
        """
        Construit une réponse d'erreur.
        
        Args:
            state: État actuel
            error_message: Message d'erreur
            
        Returns:
            Réponse d'erreur formatée
        """
        return {
            "query": state.get("query", ""),
            "answer": f"Une erreur s'est produite: {error_message}",
            "sources": [],
            "images": [],
            "tables": [],
            "metadata": {
                "error": error_message,
                "processing_time": state.get("processing_time", 0.0),
                "agent_trace": state.get("agent_trace", [])
            },
            "success": False,
            "error": error_message
        }
    
    def _update_conversation_memory(self, state: RegulationState) -> None:
        """
        Met à jour la mémoire conversationnelle avec l'échange actuel.
        
        Args:
            state: État contenant la requête et la réponse
        """
        if not self.memory_service:
            return
        
        query = state["query"]
        answer = state.get("answer", "")
        
        try:
            # Ajouter l'échange à la mémoire via le service existant
            self.memory_service.add_exchange(
                user_message=query,
                assistant_message=answer,
                metadata={
                    "processing_time": state.get("processing_time", 0.0),
                    "sources_used": len(state.get("sources", [])),
                    "domain": state.get("routing_decision", {}).get("domain", "general")
                }
            )
        except Exception as e:
            # Log l'erreur mais ne pas faire échouer le processus principal
            state["agent_trace"].append(f"memory_update_failed: {str(e)}")
    
    def generate_streaming_response(self, state: RegulationState) -> Generator[str, None, None]:
        """
        Génère une réponse en streaming.
        
        Args:
            state: État préparé pour la génération
            
        Yields:
            Chunks de réponse en streaming
        """
        generation_params = self._prepare_generation_parameters(state)
        
        try:
            # Utiliser le mode streaming du service de génération
            for chunk in self.generation_service.generate_response_stream(**generation_params):
                yield chunk
                
        except Exception as e:
            yield f"Erreur lors de la génération: {str(e)}"