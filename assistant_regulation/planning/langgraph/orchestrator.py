"""
LangGraph Orchestrator - Orchestrateur Principal
===============================================

Orchestrateur principal utilisant LangGraph pour coordonner
tous les agents et services existants dans une architecture multi-agent.
"""

from typing import Dict, Optional, Generator, Any
import time
from .state.regulation_state import RegulationState
from .agents import (
    SupervisorAgent,
    RoutingAgent,
    RetrievalAgent,
    ValidationAgent,
    GenerationAgent
)
from .workflows.regulation_workflow import (
    create_regulation_workflow,
    create_simple_workflow,
    create_debug_workflow,
    get_workflow_config
)
from .workflows.streaming_workflow import (
    create_streaming_workflow,
    StreamingWorkflowExecutor,
    create_fast_streaming_workflow
)

# Import des services existants
from assistant_regulation.planning.services import (
    RetrievalService,
    GenerationService,
    MemoryService,
    ValidationService,
    ContextBuilderService,
    RerankerService
)
from assistant_regulation.planning.services.master_routing_service import MasterRoutingService
from assistant_regulation.planning.services.intelligent_routing_service import IntelligentRoutingService
from assistant_regulation.planning.services.knowledge_routing_service import KnowledgeRoutingService
from assistant_regulation.planning.agents.query_analysis_agent import QueryAnalysisAgent


class LangGraphOrchestrator:
    """
    Orchestrateur principal utilisant LangGraph pour coordonner
    une architecture multi-agent avec vos services existants.
    
    Remplace le ModularOrchestrator avec une approche basée sur LangGraph
    tout en réutilisant 100% de vos services métier existants.
    """
    
    def __init__(
        self,
        *,
        llm_provider: str = "ollama",
        model_name: str = "llama3.2",
        enable_verification: bool = True,
        workflow_type: str = "full",
        enable_debug: bool = False,
        # Services existants (optionnels - seront créés si non fournis)
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
        """
        Initialise l'orchestrateur LangGraph.
        
        Args:
            llm_provider: Fournisseur LLM ("ollama" ou "mistral")
            model_name: Nom du modèle à utiliser
            enable_verification: Activer la validation des chunks
            workflow_type: Type de workflow ("full", "simple", "debug", "streaming")
            enable_debug: Activer le mode debug détaillé
            **services: Services existants à réutiliser
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.enable_verification = enable_verification
        self.workflow_type = workflow_type
        self.enable_debug = enable_debug
        
        # Initialiser les services (réutiliser existants ou créer nouveaux)
        self._initialize_services(
            retrieval_service, generation_service, memory_service,
            validation_service, context_builder_service, reranker_service,
            master_routing_service, intelligent_routing_service, knowledge_routing_service
        )
        
        # Initialiser les agents LangGraph
        self._initialize_agents()
        
        # Créer les workflows
        self._initialize_workflows()
        
        # Statistiques
        self.stats = {
            "queries_processed": 0,
            "total_processing_time": 0.0,
            "errors": 0,
            "workflow_type": workflow_type
        }
    
    def _initialize_services(self, *services) -> None:
        """Initialise tous les services nécessaires."""
        import os
        rekanker_model = os.getenv("JINA_MODEL")
        
        # Décompacter les services fournis
        (retrieval_service, generation_service, memory_service,
         validation_service, context_builder_service, reranker_service,
         master_routing_service, intelligent_routing_service, knowledge_routing_service) = services
        
        # Initialiser ou réutiliser les services
        self.retrieval_service = retrieval_service or RetrievalService()
        self.generation_service = generation_service or GenerationService(
            self.llm_provider, self.model_name
        )
        
        # Memory service a besoin du client LLM
        self.memory_service = memory_service or MemoryService(
            llm_client=self.generation_service.raw_client,
            model_name=self.model_name
        )
        
        self.validation_service = (
            validation_service or ValidationService(self.llm_provider, self.model_name)
            if self.enable_verification else None
        )
        
        self.context_builder_service = context_builder_service or ContextBuilderService()
        self.reranker_service = reranker_service or RerankerService(model_name=rekanker_model)
        
        # Services de routage
        self.master_routing_service = master_routing_service or MasterRoutingService(
            self.llm_provider, self.model_name
        )
        self.intelligent_routing_service = intelligent_routing_service or IntelligentRoutingService(
            self.llm_provider, self.model_name
        )
        self.knowledge_routing_service = knowledge_routing_service or KnowledgeRoutingService(
            self.llm_provider, self.model_name
        )
        
        # Agent d'analyse de requête
        self.query_analysis_agent = QueryAnalysisAgent(self.llm_provider, self.model_name)
    
    def _initialize_agents(self) -> None:
        """Initialise tous les agents LangGraph."""
        
        # Agent superviseur
        self.supervisor_agent = SupervisorAgent(
            master_routing_service=self.master_routing_service,
            query_analysis_agent=self.query_analysis_agent
        )
        
        # Agent de routage
        self.routing_agent = RoutingAgent(
            intelligent_routing_service=self.intelligent_routing_service,
            knowledge_routing_service=self.knowledge_routing_service
        )
        
        # Agent de récupération
        self.retrieval_agent = RetrievalAgent(
            retrieval_service=self.retrieval_service,
            context_builder_service=self.context_builder_service,
            reranker_service=self.reranker_service
        )
        
        # Agent de validation
        self.validation_agent = ValidationAgent(
            validation_service=self.validation_service
        ) if self.validation_service else None
        
        # Agent de génération
        self.generation_agent = GenerationAgent(
            generation_service=self.generation_service,
            memory_service=self.memory_service
        )
    
    def _initialize_workflows(self) -> None:
        """Initialise les workflows LangGraph."""
        
        if self.workflow_type == "debug" or self.enable_debug:
            self.workflow = create_debug_workflow(
                self.supervisor_agent,
                self.routing_agent,
                self.retrieval_agent,
                self.validation_agent,
                self.generation_agent
            )
            
        elif self.workflow_type == "simple":
            self.workflow = create_simple_workflow(
                self.supervisor_agent,
                self.generation_agent
            )
            
        elif self.workflow_type == "streaming":
            self.workflow = create_streaming_workflow(
                self.supervisor_agent,
                self.routing_agent,
                self.retrieval_agent,
                self.validation_agent,
                self.generation_agent
            )
            
        else:  # "full" par défaut
            self.workflow = create_regulation_workflow(
                self.supervisor_agent,
                self.routing_agent,
                self.retrieval_agent,
                self.validation_agent,
                self.generation_agent
            )
        
        # Workflow streaming séparé
        self.streaming_workflow = create_streaming_workflow(
            self.supervisor_agent,
            self.routing_agent,
            self.retrieval_agent,
            self.validation_agent,
            self.generation_agent
        )
        
        self.streaming_executor = StreamingWorkflowExecutor(self.streaming_workflow)
    
    def process_query(
        self,
        query: str,
        *,
        use_images: bool = True,
        use_tables: bool = True,
        top_k: int = 5,
        use_conversation_context: bool = True,
        use_advanced_routing: bool = True,
    ) -> Dict[str, Any]:
        """
        Traite une requête en utilisant le workflow LangGraph.
        
        Args:
            query: Question de l'utilisateur
            use_images: Inclure les résultats d'images
            use_tables: Inclure les résultats de tableaux
            top_k: Nombre de résultats à récupérer
            use_conversation_context: Utiliser le contexte conversationnel
            use_advanced_routing: Utiliser le routage avancé
            
        Returns:
            Réponse complète avec métadonnées
        """
        start_time = time.time()
        
        try:
            # Préparer l'état initial
            initial_state = self._prepare_initial_state(
                query, use_images, use_tables, top_k,
                use_conversation_context, use_advanced_routing
            )
            
            # Exécuter le workflow avec compatibilité de version
            try:
                # Tenter d'utiliser la méthode invoke (LangGraph >= 0.2.0)
                if hasattr(self.workflow, 'invoke'):
                    final_state = self.workflow.invoke(initial_state)
                else:
                    # Fallback pour versions anciennes
                    final_state = self._simulate_workflow_execution(initial_state)
            except AttributeError:
                # Double fallback si invoke n'existe pas
                final_state = self._simulate_workflow_execution(initial_state)
            
            # Extraire et formater la réponse
            response = self._extract_final_response(final_state)
            
            # Mettre à jour les statistiques
            self._update_stats(time.time() - start_time, success=True)
            
            return response
            
        except Exception as e:
            self._update_stats(time.time() - start_time, success=False)
            return self._build_error_response(query, str(e))
    
    def process_query_stream(
        self,
        query: str,
        *,
        use_images: bool = True,
        use_tables: bool = True,
        top_k: int = 5,
        use_conversation_context: bool = True,
        use_advanced_routing: bool = True,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Traite une requête en mode streaming.
        
        Args:
            query: Question de l'utilisateur
            **kwargs: Paramètres de traitement
            
        Yields:
            Événements de streaming
        """
        try:
            # Préparer l'état initial
            initial_state = self._prepare_initial_state(
                query, use_images, use_tables, top_k,
                use_conversation_context, use_advanced_routing
            )
            
            # Utiliser l'exécuteur streaming
            yield from self.streaming_executor.execute_stream(initial_state)
            
        except Exception as e:
            yield {
                "type": "error",
                "message": f"Erreur streaming: {str(e)}",
                "timestamp": time.time()
            }
    
    def _prepare_initial_state(
        self,
        query: str,
        use_images: bool,
        use_tables: bool,
        top_k: int,
        use_conversation_context: bool,
        use_advanced_routing: bool
    ) -> RegulationState:
        """Prépare l'état initial pour le workflow."""
        
        # Contexte conversationnel si demandé
        conversation_context = ""
        if use_conversation_context and self.memory_service:
            conversation_context = self.memory_service.get_context(query)
        
        initial_state = RegulationState(
            query=query,
            conversation_context=conversation_context,
            use_images=use_images,
            use_tables=use_tables,
            top_k=top_k,
            use_conversation_context=use_conversation_context,
            use_advanced_routing=use_advanced_routing,
            agent_trace=[],
            processing_time=0.0
        )
        
        return initial_state
    
    def _extract_final_response(self, final_state: RegulationState) -> Dict[str, Any]:
        """Extrait la réponse finale du state."""
        return final_state.get("final_response", {
            "query": final_state.get("query", ""),
            "answer": final_state.get("answer", "Réponse non disponible"),
            "sources": final_state.get("sources", []),
            "images": final_state.get("images", []),
            "tables": final_state.get("tables", []),
            "metadata": {
                "processing_time": final_state.get("processing_time", 0.0),
                "agent_trace": final_state.get("agent_trace", []),
                "error": final_state.get("error")
            },
            "success": not bool(final_state.get("error"))
        })
    
    def _simulate_workflow_execution(self, initial_state: RegulationState) -> RegulationState:
        """
        Simule l'exécution du workflow pour les versions LangGraph anciennes.
        Utilise directement vos services existants dans l'ordre correct.
        """
        state = initial_state.copy()
        
        try:
            # 1. Supervisor Agent (analyse et routage)
            query_analysis = self.query_analysis_agent.analyse_query(state["query"])
            state["query_analysis"] = query_analysis
            
            if query_analysis.get("needs_rag", True):
                # 2. Routage avancé
                routing_decision = self.master_routing_service.route_query(state["query"])
                state["routing_decision"] = routing_decision
                
                # 3. Récupération multimodale
                search_params = {
                    "query": state["query"],
                    "conversation_context": state.get("conversation_context", ""),
                    "use_images": state.get("use_images", True),
                    "use_tables": state.get("use_tables", True),
                    "top_k": state.get("top_k", 5)
                }
                
                # Utiliser la même méthode que ModularOrchestrator
                try:
                    retrieval_results = self.retrieval_service.retrieve(
                        query=state["query"],
                        use_images=search_params.get("use_images", True),
                        use_tables=search_params.get("use_tables", True),
                        top_k=search_params.get("top_k", 5)
                    )
                except Exception as e:
                    retrieval_results = {"text": [], "images": [], "tables": [], "error": str(e)}
                state["retrieval_results"] = retrieval_results
                
                # 4. Validation (si activée)
                if self.validation_service:
                    try:
                        validation_results = self.validation_service.validate_chunks(
                            query=state["query"],
                            chunks=retrieval_results
                        )
                        state["verified_chunks"] = self._filter_validated_chunks(
                            retrieval_results, validation_results
                        )
                    except:
                        state["verified_chunks"] = retrieval_results
                else:
                    state["verified_chunks"] = retrieval_results
                
                # 5. Construction du contexte
                context = self.context_builder_service.build_context(state["verified_chunks"])
                state["context"] = context
            else:
                # Pas de RAG nécessaire
                state["context"] = ""
                state["verified_chunks"] = {}
            
            # 6. Génération de la réponse
            answer = self.generation_service.generate_answer(
                query=state["query"],
                context=state.get("context", ""),
                conversation_context=state.get("conversation_context", ""),
                temperature=0.3,
                max_tokens=1024
            )
            
            generation_result = {
                "answer": answer,
                "success": True
            }
            
            state["answer"] = generation_result.get("answer", "")
            state["generation_results"] = generation_result
            
            # 7. Mettre à jour la mémoire
            if self.memory_service:
                try:
                    self.memory_service.add_exchange(
                        user_message=state["query"],
                        assistant_message=state["answer"]
                    )
                except:
                    pass  # Ignore les erreurs de mémoire
            
            # 8. Extraire les sources pour la réponse finale
            verified_chunks = state.get("verified_chunks", {})
            if not verified_chunks or not verified_chunks.get("text"):
                verified_chunks = state.get("retrieval_results", {})
            
            # Extraire sources avec la même logique que Compatible
            state["sources"] = self._extract_sources_simple(verified_chunks.get("text", []))
            state["images"] = verified_chunks.get("images", [])
            state["tables"] = verified_chunks.get("tables", [])
            
            state["agent_trace"] = [
                "supervisor_complete", "routing_complete", 
                "retrieval_complete", "validation_complete", "generation_complete"
            ]
            
            return state
            
        except Exception as e:
            state["error"] = str(e)
            state["answer"] = f"Erreur lors de la simulation workflow: {str(e)}"
            return state
    
    def _filter_validated_chunks(self, retrieval_results, validation_results):
        """Filtre les chunks validés."""
        if not validation_results:
            return retrieval_results
        
        filtered_chunks = {}
        for source_type, chunks in retrieval_results.items():
            if isinstance(chunks, list):
                source_validation = validation_results.get(source_type, {})
                valid_indices = source_validation.get("valid_chunks", list(range(len(chunks))))
                filtered_chunks[source_type] = [
                    chunk for i, chunk in enumerate(chunks) if i in valid_indices
                ]
            else:
                filtered_chunks[source_type] = chunks
        
        return filtered_chunks
    
    def _extract_sources_simple(self, text_chunks):
        """Extrait les sources des chunks texte (version simplifiée)."""
        sources = []
        for i, chunk in enumerate(text_chunks):
            # Gestion des différents formats de chunks
            content = chunk.get('content') or chunk.get('documents') or chunk.get('text', '')
            meta = chunk.get("metadata", {})
            
            # Extraction des informations basiques
            document_name = (
                meta.get('document_name') or 
                chunk.get('document_name') or
                'Document inconnu'
            )
            
            page = meta.get('page_number') or meta.get('page_no') or None
            regulation_code = meta.get('regulation_code') or chunk.get('regulation_code') or 'Code inconnu'
            
            source_info = {
                'id': i + 1,
                'content': content,
                'document_name': document_name,
                'page': page,
                'regulation_code': regulation_code,
                'relevance_score': chunk.get('score', 0.0)
            }
            
            sources.append(source_info)
        
        return sources

    def _build_error_response(self, query: str, error: str) -> Dict[str, Any]:
        """Construit une réponse d'erreur."""
        return {
            "query": query,
            "answer": f"Désolé, une erreur s'est produite: {error}",
            "sources": [],
            "images": [],
            "tables": [],
            "metadata": {"error": error},
            "success": False,
            "error": error
        }
    
    def _update_stats(self, processing_time: float, success: bool) -> None:
        """Met à jour les statistiques."""
        self.stats["queries_processed"] += 1
        self.stats["total_processing_time"] += processing_time
        if not success:
            self.stats["errors"] += 1
    
    # ------------------------------------------------------------------
    # Méthodes de compatibilité avec ModularOrchestrator
    # ------------------------------------------------------------------
    
    def get_routing_info(self, query: str) -> Dict[str, Any]:
        """Obtient les informations de routage sans exécuter."""
        return self.master_routing_service.get_execution_plan(query)
    
    def explain_routing_decision(self, query: str) -> str:
        """Explique la décision de routage."""
        return self.master_routing_service.explain_routing_decision(query)
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de conversation."""
        return {
            **self.stats,
            "memory_stats": self.memory_service.get_stats() if self.memory_service else {}
        }
    
    def clear_conversation_memory(self) -> None:
        """Vide la mémoire conversationnelle."""
        if self.memory_service:
            self.memory_service.clear()
    
    @property
    def conversation_memory(self):
        """Accès direct au service de mémoire."""
        return self.memory_service
    
    def switch_workflow(self, workflow_type: str) -> None:
        """Change le type de workflow dynamiquement."""
        if workflow_type != self.workflow_type:
            self.workflow_type = workflow_type
            self._initialize_workflows()
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques détaillées sur les agents."""
        return {
            "workflow_type": self.workflow_type,
            "agents_initialized": {
                "supervisor": self.supervisor_agent is not None,
                "routing": self.routing_agent is not None,
                "retrieval": self.retrieval_agent is not None,
                "validation": self.validation_agent is not None,
                "generation": self.generation_agent is not None
            },
            "services_status": {
                "retrieval": self.retrieval_service is not None,
                "generation": self.generation_service is not None,
                "memory": self.memory_service is not None,
                "validation": self.validation_service is not None,
                "context_builder": self.context_builder_service is not None,
                "reranker": self.reranker_service is not None
            },
            "processing_stats": self.stats
        }