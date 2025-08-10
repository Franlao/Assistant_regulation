"""
Modular Orchestrator - Version refactorisée coordonnant des services dédiés
"""

from __future__ import annotations
from typing import Dict, Optional, Generator
import os
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
from assistant_regulation.planning.sync.query_processor import QueryProcessor
from assistant_regulation.planning.sync.response_builder import ResponseBuilder
from assistant_regulation.planning.sync.streaming_handler import StreamingHandler
from assistant_regulation.planning.sync.compatibility_adapter import CompatibilityAdapter
from dotenv import load_dotenv

load_dotenv()


class ModularOrchestrator:
    """Orchestrateur refactorisé <200 lignes coordonnant des services dédiés."""

    def __init__(
        self,
        *,
        llm_provider: str = "ollama",
        model_name: str = "llama3.2",
        enable_verification: bool = True,
        retrieval_service: Optional[RetrievalService] = None,
        generation_service: Optional[GenerationService] = None,
        memory_service: Optional[MemoryService] = None,
        validation_service: Optional[ValidationService] = None,
        context_builder_service: Optional[ContextBuilderService] = None,
        reranker_service: Optional[RerankerService] = None,
        master_routing_service: Optional[MasterRoutingService] = None,
        intelligent_routing_service: Optional[IntelligentRoutingService] = None,
        knowledge_routing_service: Optional[KnowledgeRoutingService] = None,
    ) -> None:
        
        # Initialisation des services principaux
        rekanker_model = os.getenv("JINA_MODEL")
        self.retrieval_service = retrieval_service or RetrievalService()
        self.generation_service = generation_service or GenerationService(llm_provider, model_name)
        
        # Memory a besoin du client pour résumer
        self.memory_service = memory_service or MemoryService(
            llm_client=self.generation_service.raw_client,
            model_name=model_name,
        )
        
        self.validation_service = (
            validation_service or ValidationService(llm_provider, model_name)
            if enable_verification
            else None
        )

        self.context_builder_service = context_builder_service or ContextBuilderService()
        self.reranker_service = reranker_service or RerankerService(model_name=rekanker_model)

        # Services de routage
        self.master_routing_service = master_routing_service or MasterRoutingService(llm_provider, model_name)
        self.intelligent_routing_service = intelligent_routing_service or IntelligentRoutingService(llm_provider, model_name)
        self.knowledge_routing_service = knowledge_routing_service or KnowledgeRoutingService(llm_provider, model_name)
        
        # Garde le query_analyzer existant pour la compatibilité
        self.query_analyzer = QueryAnalysisAgent(llm_provider, model_name)
        self.enable_verification = enable_verification

        # Initialisation des composants refactorisés
        self._initialize_components()

    def _initialize_components(self):
        """Initialise les composants refactorisés."""
        # Query Processor pour le traitement des requêtes
        self.query_processor = QueryProcessor(
            retrieval_service=self.retrieval_service,
            generation_service=self.generation_service,
            memory_service=self.memory_service,
            validation_service=self.validation_service,
            context_builder_service=self.context_builder_service,
            reranker_service=self.reranker_service,
            master_routing_service=self.master_routing_service,
            intelligent_routing_service=self.intelligent_routing_service,
            knowledge_routing_service=self.knowledge_routing_service,
            query_analyzer=self.query_analyzer,
            enable_verification=self.enable_verification,
        )

        # Response Builder pour construire les réponses
        self.response_builder = ResponseBuilder(self.memory_service)

        # Streaming Handler pour les réponses en streaming
        self.streaming_handler = StreamingHandler(
            query_processor=self.query_processor,
            generation_service=self.generation_service,
            memory_service=self.memory_service
        )

        # Compatibility Adapter pour la rétrocompatibilité
        self.compatibility_adapter = CompatibilityAdapter(
            generation_service=self.generation_service,
            memory_service=self.memory_service
        )

    def process_query(
        self,
        query: str,
        *,
        use_images: bool = True,
        use_tables: bool = True,
        top_k: int = 5,
        use_conversation_context: bool = True,
        use_advanced_routing: bool = True,
    ) -> Dict:
        """Point d'entrée unique : retourne une réponse au format dict."""
        
        # Contexte conversationnel facultatif
        conversation_context = (
            self.memory_service.get_context(query) if use_conversation_context else ""
        )

        # Traitement selon le routage choisi
        if use_advanced_routing:
            result = self.query_processor.process_advanced_routing(
                query, conversation_context, use_images, use_tables, top_k
            )
        else:
            result = self.query_processor.process_traditional_routing(
                query, conversation_context, use_images, use_tables, top_k
            )

        # Construction de la réponse finale
        return self.response_builder.build_response(
            query, 
            result["answer"], 
            result["chunks"], 
            result["analysis"], 
            result.get("routing_decision")
        )

    def process_query_stream(
        self,
        query: str,
        *,
        use_images: bool = True,
        use_tables: bool = True,
        top_k: int = 5,
        use_conversation_context: bool = True,
        use_advanced_routing: bool = True,
    ) -> Generator[str, None, None]:
        """Point d'entrée pour le streaming : génère une réponse en streaming."""
        
        # Contexte conversationnel facultatif
        conversation_context = (
            self.memory_service.get_context(query) if use_conversation_context else ""
        )

        # Streaming selon le routage choisi
        yield from self.streaming_handler.process_stream(
            query, conversation_context, use_images, use_tables, top_k, use_advanced_routing
        )

    # ------------------------------------------------------------------
    # Méthodes d'information sur le routage
    # ------------------------------------------------------------------
    
    def get_routing_info(self, query: str) -> Dict:
        """Retourne les informations de routage sans exécuter la requête."""
        return self.master_routing_service.get_execution_plan(query)
    
    def explain_routing_decision(self, query: str) -> str:
        """Explique la décision de routage pour une requête."""
        return self.master_routing_service.explain_routing_decision(query)

    # ------------------------------------------------------------------
    # Méthodes de compatibilité avec SimpleOrchestrator (délégation)
    # ------------------------------------------------------------------
    
    def get_conversation_stats(self) -> Dict:
        """Retourne des statistiques sur la conversation actuelle."""
        return self.compatibility_adapter.get_conversation_stats()
    
    def clear_conversation_memory(self):
        """Vide la mémoire conversationnelle."""
        self.compatibility_adapter.clear_conversation_memory()
    
    def export_conversation(self) -> Dict:
        """Exporte la conversation actuelle."""
        return self.compatibility_adapter.export_conversation()
    
    @property
    def conversation_memory(self):
        """Accès direct au service de mémoire pour compatibilité."""
        return self.compatibility_adapter.conversation_memory
    
    @property 
    def llm_provider(self) -> str:
        """Provider LLM pour compatibilité."""
        return self.compatibility_adapter.llm_provider
    
    @llm_provider.setter
    def llm_provider(self, value: str):
        """Setter pour llm_provider pour compatibilité."""
        self.compatibility_adapter.llm_provider = value
    
    @property
    def model_name(self) -> str:
        """Nom du modèle pour compatibilité.""" 
        return self.compatibility_adapter.model_name
    
    @model_name.setter
    def model_name(self, value: str):
        """Setter pour model_name pour compatibilité."""
        self.compatibility_adapter.model_name = value
    
    @property 
    def enable_verification(self) -> bool:
        """État de la vérification pour compatibilité."""
        return self.validation_service is not None
    
    @enable_verification.setter
    def enable_verification(self, value: bool):
        """Setter pour enable_verification pour compatibilité."""
        # Pour la compatibilité, on ne fait rien car le service est défini à l'initialisation
        pass 