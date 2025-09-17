"""
Streaming Handler - Gère les réponses en streaming
"""

from typing import Generator, Dict
from assistant_regulation.planning.services import GenerationService, MemoryService
from .query_processor import QueryProcessor


class StreamingHandler:
    """Gère les réponses en streaming."""
    
    def __init__(
        self, 
        query_processor: QueryProcessor,
        generation_service: GenerationService,
        memory_service: MemoryService
    ):
        self.query_processor = query_processor
        self.generation_service = generation_service
        self.memory_service = memory_service

    def process_stream(
        self,
        query: str,
        conversation_context: str,
        use_images: bool,
        use_tables: bool,
        top_k: int,
        use_advanced_routing: bool = True,
    ) -> Generator[str, None, None]:
        """Point d'entrée pour le streaming : génère une réponse en streaming."""

        print(f"[STREAMING HANDLER] Advanced routing: {use_advanced_routing}")

        if use_advanced_routing:
            yield from self._process_advanced_routing_stream(
                query, conversation_context, use_images, use_tables, top_k
            )
        else:
            yield from self._process_traditional_routing_stream(
                query, conversation_context, use_images, use_tables, top_k
            )

    def _process_advanced_routing_stream(
        self,
        query: str,
        conversation_context: str,
        use_images: bool,
        use_tables: bool,
        top_k: int,
    ) -> Generator[str, None, None]:
        """Traitement avec streaming et routage avancé."""

        print(f"[ADVANCED ROUTING] Processing query with advanced routing...")

        # Étape 1: Obtenir la décision de routage maître
        routing_decision = self.query_processor.master_routing_service.route_query(query)
        print(f"[ROUTING DECISION] Strategy: {routing_decision.response_strategy.value}")
        
        # Étape 2: Émettre un chunk d'analyse avec les informations de routage
        analysis_data = {
            "needs_rag": routing_decision.response_strategy.value != "direct_llm",
            "confidence": routing_decision.confidence_score,
            "query_type": routing_decision.response_strategy.value,
            "routing_decision": {
                "response_strategy": routing_decision.response_strategy.value,
                "confidence_score": routing_decision.confidence_score,
                "search_config": routing_decision.search_config or {},
                "reasoning": routing_decision.reasoning
            }
        }
        
        yield {
            "type": "analysis", 
            "content": analysis_data
        }
        
        # Étape 3: Exécuter selon la stratégie déterminée
        if routing_decision.response_strategy.value == "meta_query":
            # Question méta - traitement direct sans streaming LLM
            yield from self._process_meta_query_stream(query, routing_decision)
            
        elif routing_decision.response_strategy.value == "direct_llm":
            # Réponse directe du LLM en streaming
            yield from self.generation_service.generate_answer_stream(
                query,
                conversation_context=conversation_context,
            )
                
        elif routing_decision.response_strategy.value == "vector_search":
            # Recherche vectorielle avec routage intelligent
            chunks = self.query_processor._execute_intelligent_search(
                routing_decision.search_config,
                use_images,
                use_tables,
                top_k
            )
            
            # Rerank et validation
            chunks = self.query_processor._process_chunks(query, chunks, top_k)

            # Traiter les chunks pour extraire les sources avec liens  
            # Les chunks du RetrievalService sont organisés par type: chunks["text"], chunks["images"], chunks["tables"]
            text_chunks = chunks.get("text", []) if isinstance(chunks, dict) else []
            
            from .response_builder import ResponseBuilder
            processed_sources = ResponseBuilder._extract_sources(text_chunks)
            
            # Émettre les résultats de recherche
            yield {
                "type": "search_complete",
                "content": {
                    "sources": processed_sources,
                    "images": chunks.get("images", []) if isinstance(chunks, dict) else [],
                    "tables": chunks.get("tables", []) if isinstance(chunks, dict) else []
                }
            }
            
            # Génération de réponse en streaming
            context = self.query_processor.context_builder_service.build_context(chunks)
            yield from self.generation_service.generate_answer_stream(
                query,
                context=context,
                conversation_context=conversation_context,
            )
                
        else:  # hybrid_response
            # Approche hybride en streaming
            chunks = self.query_processor._execute_intelligent_search(
                routing_decision.search_config,
                use_images,
                use_tables,
                top_k
            )
            
            chunks = self.query_processor._process_chunks(query, chunks, top_k)
            
            # Émettre les résultats de recherche
            yield {
                "type": "search_complete",
                "content": {
                    "sources": [c for c in chunks if c.get("chunk_type") == "text"],
                    "images": [c for c in chunks if c.get("chunk_type") == "image"],
                    "tables": [c for c in chunks if c.get("chunk_type") == "table"]
                }
            }
            
            # Générer réponse enrichie en streaming
            context = self.query_processor.context_builder_service.build_context(chunks)
            yield from self.generation_service.generate_answer_stream(
                query,
                context=context,
                conversation_context=conversation_context,
            )
        
        # Étape finale: Émettre un chunk de finalisation
        yield {
            "type": "done",
            "content": {
                "routing_decision": analysis_data["routing_decision"]
            }
        }

    def _process_traditional_routing_stream(
        self,
        query: str,
        conversation_context: str,
        use_images: bool,
        use_tables: bool,
        top_k: int,
    ) -> Generator[str, None, None]:
        """Traitement avec streaming et routage traditionnel."""
        
        analysis = self.query_processor.query_analyzer.analyse_query(query)

        # Émettre un chunk d'analyse
        yield {
            "type": "analysis", 
            "content": analysis
        }

        # -------------------
        # 1. RAG if needed
        # -------------------
        if analysis["needs_rag"]:
            chunks = self.query_processor.retrieval_service.retrieve(
                query,
                use_images=use_images,
                use_tables=use_tables,
                top_k=top_k,
            )

            chunks = self.query_processor._process_chunks(query, chunks, top_k)

            # Traiter les chunks pour extraire les sources avec liens
            text_chunks = [c for c in chunks if isinstance(c, dict) and c.get("chunk_type") == "text"]
            from .response_builder import ResponseBuilder
            processed_sources = ResponseBuilder._extract_sources(text_chunks)
            
            # Émettre les résultats de recherche
            yield {
                "type": "search_complete",
                "content": {
                    "sources": processed_sources,
                    "images": chunks.get("images", []) if isinstance(chunks, dict) else [],
                    "tables": chunks.get("tables", []) if isinstance(chunks, dict) else []
                }
            }
            
            context = self.query_processor.context_builder_service.build_context(chunks)
            yield from self.generation_service.generate_answer_stream(
                query,
                context=context,
                conversation_context=conversation_context,
            )
        # -------------------
        # 2. Direct LLM
        # -------------------
        else:
            yield from self.generation_service.generate_answer_stream(
                query,
                conversation_context=conversation_context,
            )
        
        # Étape finale
        yield {
            "type": "done",
            "content": {}
        }
    
    def _process_meta_query_stream(self, query: str, routing_decision) -> Generator[str, None, None]:
        """Traite les questions méta en streaming (simulation)"""
        
        try:
            # Récupérer le service méta du query processor
            meta_service = self.query_processor.master_routing_service.meta_service
            
            # Utiliser directement la configuration de routage pour éviter de re-détecter
            search_config = routing_decision.search_config
            
            if search_config and search_config.get('query_type'):
                # Créer une détection simulée à partir de la config de routage
                from assistant_regulation.planning.services.database_meta_service import MetaDetectionResult, MetaQueryType
                
                detection_result = MetaDetectionResult(
                    is_meta=True,
                    query_type=MetaQueryType(search_config['query_type']),
                    confidence=search_config.get('confidence', 0.8),
                    extracted_params=search_config.get('extracted_params', {}),
                    reasoning=search_config.get('reasoning', 'Routing decision')
                )
                
                # Exécuter directement la requête méta avec la détection
                meta_result = meta_service.execute_meta_query(detection_result, query)
            else:
                # Fallback: utiliser la méthode normale
                meta_result = meta_service.process_query(query)
            
            if meta_result and meta_result.get("type") == "meta_answer":
                # Enregistrer dans la mémoire
                self.memory_service.add_turn(query, meta_result["answer"])
                
                # Utiliser le service de génération pour streamer la réponse méta
                answer = meta_result["answer"]
                yield from self.generation_service.generate_answer_stream(
                    query,
                    context=answer,  # Utiliser la réponse méta comme contexte
                    conversation_context="",
                )
                
                # Émettre les détails méta optionnels
                if meta_result.get("meta_details"):
                    yield {
                        "type": "meta_details",
                        "content": meta_result["meta_details"]
                    }
                    
            else:
                # Erreur ou question non-méta - émettre un message d'erreur
                error_message = meta_result.get("message", "Erreur lors du traitement de la question méta") if meta_result else "Service méta indisponible"
                
                yield {
                    "type": "text", 
                    "content": f"Désolé, je n'ai pas pu traiter votre question méta: {error_message}"
                }
                
        except Exception as e:
            yield {
                "type": "text",
                "content": f"Erreur lors du traitement de la question méta: {str(e)}"
            } 