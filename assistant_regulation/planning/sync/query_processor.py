"""
Query Processor - Gère le traitement et le routage des requêtes
"""

from typing import Dict, Optional
from assistant_regulation.planning.services import (
    RetrievalService,
    GenerationService,
    MemoryService,
    ValidationService,
    ContextBuilderService,
    RerankerService,
)
from assistant_regulation.planning.services.master_routing_service import MasterRoutingService
from assistant_regulation.planning.services.intelligent_routing_service import IntelligentRoutingService
from assistant_regulation.planning.services.knowledge_routing_service import KnowledgeRoutingService
from assistant_regulation.planning.agents.query_analysis_agent import QueryAnalysisAgent


class QueryProcessor:
    """Traite les requêtes selon différentes stratégies de routage."""
    
    def __init__(
        self,
        retrieval_service: RetrievalService,
        generation_service: GenerationService,
        memory_service: MemoryService,
        validation_service: Optional[ValidationService],
        context_builder_service: ContextBuilderService,
        reranker_service: RerankerService,
        master_routing_service: MasterRoutingService,
        intelligent_routing_service: IntelligentRoutingService,
        knowledge_routing_service: KnowledgeRoutingService,
        query_analyzer: QueryAnalysisAgent,
        enable_verification: bool = True,
    ):
        self.retrieval_service = retrieval_service
        self.generation_service = generation_service
        self.memory_service = memory_service
        self.validation_service = validation_service
        self.context_builder_service = context_builder_service
        self.reranker_service = reranker_service
        self.master_routing_service = master_routing_service
        self.intelligent_routing_service = intelligent_routing_service
        self.knowledge_routing_service = knowledge_routing_service
        self.query_analyzer = query_analyzer
        self.enable_verification = enable_verification

    def process_advanced_routing(
        self,
        query: str,
        conversation_context: str,
        use_images: bool,
        use_tables: bool,
        top_k: int,
    ) -> Dict:
        """Traitement avec le nouveau système de routage avancé."""
        
        # Étape 1: Obtenir la décision de routage maître
        routing_decision = self.master_routing_service.route_query(query)
        
        # Étape 2: Exécuter selon la stratégie déterminée
        if routing_decision.response_strategy.value == "direct_llm":
            return self._process_direct_llm(query, conversation_context, routing_decision)
            
        elif routing_decision.response_strategy.value == "vector_search":
            return self._process_vector_search(
                query, conversation_context, routing_decision, 
                use_images, use_tables, top_k
            )
            
        else:  # hybrid_response
            return self._process_hybrid_response(
                query, conversation_context, routing_decision,
                use_images, use_tables, top_k
            )

    def process_traditional_routing(
        self,
        query: str,
        conversation_context: str,
        use_images: bool,
        use_tables: bool,
        top_k: int,
    ) -> Dict:
        """Traitement avec l'ancien système de routage."""
        
        analysis = self.query_analyzer.analyse_query(query)

        if analysis["needs_rag"]:
            chunks = self.retrieval_service.retrieve(
                query,
                use_images=use_images,
                use_tables=use_tables,
                top_k=top_k,
            )
            chunks = self._process_chunks(query, chunks, top_k)
            context = self.context_builder_service.build_context(chunks)
            answer = self.generation_service.generate_answer(
                query,
                context=context,
                conversation_context=conversation_context,
            )
        else:
            answer = self.generation_service.generate_answer(
                query,
                conversation_context=conversation_context,
            )
            chunks = {"text": [], "images": [], "tables": []}

        return {"answer": answer, "chunks": chunks, "analysis": analysis}

    def _process_direct_llm(self, query: str, conversation_context: str, routing_decision) -> Dict:
        """Traite une requête avec réponse directe du LLM."""
        answer = self.generation_service.generate_answer(
            query,
            conversation_context=conversation_context,
        )
        chunks = {"text": [], "images": [], "tables": []}
        analysis = {"needs_rag": False, "query_type": "general"}
        
        return {
            "answer": answer, 
            "chunks": chunks, 
            "analysis": analysis, 
            "routing_decision": routing_decision
        }

    def _process_vector_search(
        self, query: str, conversation_context: str, routing_decision,
        use_images: bool, use_tables: bool, top_k: int
    ) -> Dict:
        """Traite une requête avec recherche vectorielle."""
        chunks = self._execute_intelligent_search(
            routing_decision.search_config,
            use_images,
            use_tables,
            top_k
        )
        
        chunks = self._process_chunks(query, chunks, top_k)
        context = self.context_builder_service.build_context(chunks)
        answer = self.generation_service.generate_answer(
            query,
            context=context,
            conversation_context=conversation_context,
        )
        analysis = {
            "needs_rag": True, 
            "query_type": routing_decision.search_config.get("search_type", "unknown")
        }
        
        return {
            "answer": answer,
            "chunks": chunks, 
            "analysis": analysis,
            "routing_decision": routing_decision
        }

    def _process_hybrid_response(
        self, query: str, conversation_context: str, routing_decision,
        use_images: bool, use_tables: bool, top_k: int
    ) -> Dict:
        """Traite une requête avec approche hybride."""
        chunks = self._execute_intelligent_search(
            routing_decision.search_config,
            use_images,
            use_tables,
            top_k
        )
        
        chunks = self._process_chunks(query, chunks, top_k)
        context = self.context_builder_service.build_context(chunks)
        answer = self.generation_service.generate_answer(
            query,
            context=context,
            conversation_context=conversation_context,
        )
        analysis = {"needs_rag": True, "query_type": "hybrid"}

        return {
            "answer": answer,
            "chunks": chunks,
            "analysis": analysis, 
            "routing_decision": routing_decision
        }

    def _execute_intelligent_search(
        self,
        search_config: Dict,
        use_images: bool,
        use_tables: bool,
        top_k: int,
    ) -> Dict:
        """Exécute une recherche selon la configuration du routage intelligent."""
        
        search_type = search_config.get("search_type", "classic")
        params = search_config.get("params", {})
        
        if search_type == "by_regulation":
            text_results = self.retrieval_service.search_by_regulation(
                regulation_code=params.get("regulation_code"),
                query=params.get("query"),
                top_k=top_k,
            )
            return self._complete_multimodal_search(
                text_results, params.get("query"), use_images, use_tables, top_k
            )
            
        elif search_type == "full_regulation":
            text_results = self.retrieval_service.get_all_chunks_for_regulation(
                regulation_code=params.get("regulation_code")
            )
            return self._complete_multimodal_search(
                text_results, params.get("query", ""), use_images, use_tables, top_k
            )
            
        elif search_type == "multiple_regulations":
            text_results = self.retrieval_service.search_multiple_regulations(
                regulation_codes=params.get("regulation_codes", []),
                query=params.get("query"),
                top_k=top_k,
            )
            return self._complete_multimodal_search(
                text_results, params.get("query"), use_images, use_tables, top_k
            )
            
        elif search_type == "compare_regulations":
            text_results = self.retrieval_service.compare_regulations(
                regulation_codes=params.get("regulation_codes", []),
                query=params.get("query"),
                top_k=top_k,
            )
            return self._complete_multimodal_search(
                text_results, params.get("query"), use_images, use_tables, top_k
            )
            
        else:  # classic
            return self.retrieval_service.retrieve(
                query=params.get("query"),
                use_images=use_images,
                use_tables=use_tables,
                top_k=top_k,
            )

    def _process_chunks(self, query: str, chunks: Dict, top_k: int) -> Dict:
        """Traite les chunks (reranking et validation)."""
        
        # Rerank les chunks pour maximiser la pertinence
        for chunk_type in ["text", "images", "tables"]:
            if chunks.get(chunk_type):
                chunks[chunk_type] = self.reranker_service.rerank_chunks(
                    query, chunks[chunk_type], top_k=10
                )
        
        # Validation si activée
        if self.enable_verification and self.validation_service:
            chunks = self.validation_service.validate_chunks(query, chunks)
            
        return chunks

    def _complete_multimodal_search(
        self, 
        text_results, 
        query: str, 
        use_images: bool, 
        use_tables: bool, 
        top_k: int
    ) -> Dict:
        """Complète une recherche textuelle avec images et tables si demandé."""
        
        # Normaliser text_results en format dict
        if isinstance(text_results, list):
            chunks = {"text": text_results, "images": [], "tables": []}
        elif isinstance(text_results, dict):
            chunks = text_results
        else:
            chunks = {"text": [], "images": [], "tables": []}
        
        # Ajouter recherche d'images si demandé
        if use_images and query:
            try:
                image_results = self.retrieval_service.image_retriever.search(query, top_k=top_k)
                chunks["images"] = image_results if isinstance(image_results, list) else []
            except Exception:
                chunks["images"] = []
        
        # Ajouter recherche de tables si demandé  
        if use_tables and query:
            try:
                table_results = self.retrieval_service.table_retriever.search(query, top_k=top_k)
                chunks["tables"] = table_results if isinstance(table_results, list) else []
            except Exception:
                chunks["tables"] = []
        
        return chunks 