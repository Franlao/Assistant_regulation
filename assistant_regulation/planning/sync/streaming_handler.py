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
        
        # Étape 1: Obtenir la décision de routage maître
        routing_decision = self.query_processor.master_routing_service.route_query(query)
        
        # Étape 2: Exécuter selon la stratégie déterminée
        if routing_decision.response_strategy.value == "direct_llm":
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
            
            # Générer réponse enrichie en streaming
            context = self.query_processor.context_builder_service.build_context(chunks)
            yield from self.generation_service.generate_answer_stream(
                query,
                context=context,
                conversation_context=conversation_context,
            )

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