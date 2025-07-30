"""
LangGraph Orchestrator Compatible
=================================

Version compatible qui fonctionne même avec des versions
anciennes de LangGraph en utilisant vos services existants.
"""

from typing import Dict, Optional, Generator, Any
import time
from .state.regulation_state import RegulationState

# Import des services existants (qui fonctionnent)
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


class CompatibleLangGraphOrchestrator:
    """
    Orchestrateur compatible qui simule LangGraph mais utilise
    vos services existants qui fonctionnent déjà parfaitement.
    
    Cette version évite les problèmes d'API LangGraph tout en
    offrant les mêmes fonctionnalités.
    """
    
    def __init__(
        self,
        *,
        llm_provider: str = "mistral",
        model_name: str = "mistral-medium",
        enable_verification: bool = True,
        workflow_type: str = "full",
        enable_debug: bool = False,
        **kwargs
    ) -> None:
        """
        Initialise l'orchestrateur compatible.
        
        Args:
            llm_provider: Fournisseur LLM
            model_name: Nom du modèle
            enable_verification: Activer la validation
            workflow_type: Type de workflow simulé
            enable_debug: Mode debug
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.enable_verification = enable_verification
        self.workflow_type = workflow_type
        self.enable_debug = enable_debug
        
        # Initialiser les services (qui fonctionnent)
        self._initialize_services()
        
        # Simuler les agents LangGraph
        self._initialize_simulated_agents()
        
        # Statistiques
        self.stats = {
            "queries_processed": 0,
            "total_processing_time": 0.0,
            "errors": 0,
            "workflow_type": workflow_type,
            "mode": "compatible_simulation"
        }
        
        if enable_debug:
            print(f"[OK] CompatibleLangGraphOrchestrator initialisé")
            print(f"  - Provider: {llm_provider}")
            print(f"  - Modèle: {model_name}")
            print(f"  - Workflow: {workflow_type}")
    
    def _initialize_services(self) -> None:
        """Initialise tous les services existants."""
        import os
        rekanker_model = os.getenv("JINA_MODEL")
        
        # Services principaux (qui fonctionnent)
        self.retrieval_service = RetrievalService()
        self.generation_service = GenerationService(self.llm_provider, self.model_name)
        
        self.memory_service = MemoryService(
            llm_client=self.generation_service.raw_client,
            model_name=self.model_name
        )
        
        self.validation_service = (
            ValidationService(self.llm_provider, self.model_name)
            if self.enable_verification else None
        )
        
        self.context_builder_service = ContextBuilderService()
        self.reranker_service = RerankerService(model_name=rekanker_model)
        
        # Services de routage
        self.master_routing_service = MasterRoutingService(self.llm_provider, self.model_name)
        self.intelligent_routing_service = IntelligentRoutingService(self.llm_provider, self.model_name)
        self.knowledge_routing_service = KnowledgeRoutingService(self.llm_provider, self.model_name)
        
        # Agent d'analyse
        self.query_analysis_agent = QueryAnalysisAgent(self.llm_provider, self.model_name)
    
    def _initialize_simulated_agents(self) -> None:
        """Initialise les agents simulés."""
        self.agents_status = {
            "supervisor": True,
            "routing": True,
            "retrieval": True,
            "validation": self.validation_service is not None,
            "generation": True
        }
    
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
        Traite une requête en simulant le workflow LangGraph.
        
        Cette méthode utilise vos services existants dans un ordre
        qui simule l'exécution d'agents LangGraph.
        """
        start_time = time.time()
        
        try:
            if self.enable_debug:
                print(f"[START] Début traitement: {query}")
            
            # 1. SUPERVISOR AGENT (simulation)
            state = self._simulate_supervisor_agent(
                query, use_images, use_tables, top_k,
                use_conversation_context, use_advanced_routing
            )
            
            # 2. ROUTING AGENT (simulation)
            if state.get("needs_rag", True):
                state = self._simulate_routing_agent(state)
                
                # 3. RETRIEVAL AGENT (simulation)
                state = self._simulate_retrieval_agent(state)
                
                # 4. VALIDATION AGENT (simulation)
                if self.validation_service:
                    state = self._simulate_validation_agent(state)
            
            # 5. GENERATION AGENT (simulation)
            state = self._simulate_generation_agent(state)
            
            # 6. Construire la réponse finale
            final_response = self._build_final_response(state, start_time)
            
            # Statistiques
            self._update_stats(time.time() - start_time, success=True)
            
            if self.enable_debug:
                print(f"[DONE] Traitement terminé en {time.time() - start_time:.2f}s")
            
            return final_response
            
        except Exception as e:
            error_response = self._build_error_response(query, str(e), start_time)
            self._update_stats(time.time() - start_time, success=False)
            return error_response
    
    def _simulate_supervisor_agent(self, query, use_images, use_tables, top_k, use_conversation_context, use_advanced_routing):
        """Simule l'agent superviseur."""
        if self.enable_debug:
            print("  [SUPERVISOR] Analyse de la requête...")
        
        # Analyser la requête
        query_analysis = self.query_analysis_agent.analyse_query(query)
        
        # Contexte conversationnel
        conversation_context = ""
        if use_conversation_context and self.memory_service:
            conversation_context = self.memory_service.get_context(query)
        
        state = {
            "query": query,
            "conversation_context": conversation_context,
            "use_images": use_images,
            "use_tables": use_tables,
            "top_k": top_k,
            "use_advanced_routing": use_advanced_routing,
            "query_analysis": query_analysis,
            "needs_rag": query_analysis.get("needs_rag", True),
            "agent_trace": ["supervisor_complete"]
        }
        
        return state
    
    def _simulate_routing_agent(self, state):
        """Simule l'agent de routage."""
        if self.enable_debug:
            print("  [ROUTING] Détermination de la stratégie...")
        
        query = state["query"]
        query_analysis = state["query_analysis"]
        
        # Routage avec vos services existants
        routing_decision = self.master_routing_service.route_query(query)
        
        state["routing_decision"] = routing_decision
        state["agent_trace"].append("routing_complete")
        
        return state
    
    def _simulate_retrieval_agent(self, state):
        """Simule l'agent de récupération."""
        if self.enable_debug:
            print("  [RETRIEVAL] Recherche multimodale...")
        
        query = state["query"]
        conversation_context = state.get("conversation_context", "")
        
        # Utiliser votre service de récupération existant
        search_params = {
            "query": query,
            "conversation_context": conversation_context,
            "use_images": state.get("use_images", True),
            "use_tables": state.get("use_tables", True),
            "top_k": state.get("top_k", 5)
        }
        
        # Utiliser la même méthode que ModularOrchestrator
        try:
            retrieval_results = self.retrieval_service.retrieve(
                query=query,
                use_images=search_params.get("use_images", True),
                use_tables=search_params.get("use_tables", True),
                top_k=search_params.get("top_k", 5)
            )
            # Debug: sauvegarder pour inspection
            self._last_retrieval_results = retrieval_results
        except Exception as e:
            # Fallback si erreur
            retrieval_results = {"text": [], "images": [], "tables": [], "error": str(e)}
        
        # Reranking si disponible (même logique que ModularOrchestrator)
        try:
            reranked_results = retrieval_results.copy()
            top_k = state.get("top_k", 5)
            
            # Rerank chaque type de chunk séparément comme dans ModularOrchestrator
            for chunk_type in ["text", "images", "tables"]:
                if reranked_results.get(chunk_type):
                    reranked_results[chunk_type] = self.reranker_service.rerank_chunks(
                        query, reranked_results[chunk_type], top_k=10
                    )
            
            state["retrieval_results"] = reranked_results
            
            if self.enable_debug:
                print(f"    [DEBUG] Reranking réussi - chunks reranqués: {len(reranked_results.get('text', []))}")
        except Exception as e:
            state["retrieval_results"] = retrieval_results
            
            if self.enable_debug:
                print(f"    [DEBUG] Reranking échoué ({e}) - utilisation directe: {len(retrieval_results.get('text', []))}")
        
        state["agent_trace"].append("retrieval_complete")
        
        return state
    
    def _simulate_validation_agent(self, state):
        """Simule l'agent de validation."""
        if self.enable_debug:
            print("  [VALIDATION] Validation des chunks...")
        
        query = state["query"]
        retrieval_results = state.get("retrieval_results", {})
        
        # Validation avec votre service existant (signature correcte)
        try:
            validation_results = self.validation_service.validate_chunks(
                query=query,
                chunks=retrieval_results
            )
            state["validation_results"] = validation_results
            state["verified_chunks"] = self._filter_validated_chunks(retrieval_results, validation_results)
            
            if self.enable_debug:
                print(f"    [DEBUG] Validation réussie - chunks validés: {len(state['verified_chunks'].get('text', []))}")
        except Exception as e:
            # En cas d'erreur, utiliser les résultats sans validation
            state["verified_chunks"] = retrieval_results
            state["validation_results"] = {"skipped": True}
            
            if self.enable_debug:
                print(f"    [DEBUG] Validation échouée ({e}) - utilisation directe: {len(retrieval_results.get('text', []))}")
        
        state["agent_trace"].append("validation_complete")
        
        return state
    
    def _simulate_generation_agent(self, state):
        """Simule l'agent de génération."""
        if self.enable_debug:
            print("  [GENERATION] Génération de la réponse...")
        
        query = state["query"]
        conversation_context = state.get("conversation_context", "")
        
        # Construire le contexte - prendre les chunks de validation d'abord, sinon récupération
        verified_chunks = state.get("verified_chunks", {})
        if not verified_chunks or not verified_chunks.get("text"):
            # Si pas de chunks validés, utiliser les résultats de récupération
            verified_chunks = state.get("retrieval_results", {})
        
        if self.enable_debug:
            print(f"    [DEBUG] Chunks pour contexte: {len(verified_chunks.get('text', []))}")
        
        context = self.context_builder_service.build_context(verified_chunks)
        
        # Génération avec votre service existant
        generation_params = {
            "query": query,
            "context": context,
            "conversation_context": conversation_context,
            "include_sources": True
        }
        
        # Utiliser generate_answer au lieu de generate_response
        answer = self.generation_service.generate_answer(
            query=query,
            context=context,
            conversation_context=conversation_context,
            temperature=0.3,
            max_tokens=1024
        )
        
        generation_result = {
            "answer": answer,
            "success": True
        }
        
        state["answer"] = generation_result.get("answer", "")
        state["context"] = context
        state["generation_results"] = generation_result
        state["agent_trace"].append("generation_complete")
        
        # Mettre à jour la mémoire
        if self.memory_service:
            try:
                self.memory_service.add_exchange(
                    user_message=query,
                    assistant_message=state["answer"]
                )
            except:
                pass  # Ignore les erreurs de mémoire
        
        return state
    
    def _filter_validated_chunks(self, retrieval_results, validation_results):
        """Filtre les chunks validés."""
        if not validation_results or validation_results.get("skipped"):
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
    
    def _build_final_response(self, state, start_time):
        """Construit la réponse finale."""
        query = state["query"]
        answer = state.get("answer", "")
        
        # Extraire les sources - utiliser les chunks les plus récents disponibles
        verified_chunks = state.get("verified_chunks", {})
        if not verified_chunks or not verified_chunks.get("text"):
            # Si pas de chunks validés, utiliser les résultats de récupération
            verified_chunks = state.get("retrieval_results", {})
        
        text_chunks = verified_chunks.get("text", [])
        
        if self.enable_debug:
            print(f"    [DEBUG] verified_chunks keys: {list(verified_chunks.keys())}")
            print(f"    [DEBUG] text_chunks count: {len(text_chunks)}")
        
        sources = self._extract_sources(text_chunks)
        images = verified_chunks.get("images", [])
        tables = verified_chunks.get("tables", [])
        
        processing_time = time.time() - start_time
        
        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "images": images,
            "tables": tables,
            "metadata": {
                "orchestrator": "compatible_langgraph",
                "workflow_type": self.workflow_type,
                "processing_time": processing_time,
                "agent_trace": state.get("agent_trace", []),
                "query_analysis": state.get("query_analysis", {}),
                "routing_decision": state.get("routing_decision", {}),
                "validation_performed": "validation_results" in state
            },
            "success": True
        }
    
    def _build_error_response(self, query, error, start_time):
        """Construit une réponse d'erreur."""
        return {
            "query": query,
            "answer": f"Désolé, une erreur s'est produite: {error}",
            "sources": [],
            "images": [],
            "tables": [],
            "metadata": {
                "orchestrator": "compatible_langgraph",
                "error": error,
                "processing_time": time.time() - start_time
            },
            "success": False,
            "error": error
        }
    
    def _extract_sources(self, text_chunks):
        """Extrait les sources des chunks texte (copié de ResponseBuilder)."""
        sources = []
        for i, chunk in enumerate(text_chunks):
            # Gestion des différents formats de chunks
            content = chunk.get('content') or chunk.get('documents') or chunk.get('text', '')
            meta = chunk.get("metadata", {})
            
            # Debug: afficher la structure du chunk pour comprendre
            if self.enable_debug and i == 0:
                print(f"    [DEBUG] Chunk structure: {list(chunk.keys())}")
                print(f"    [DEBUG] Content preview: {content[:100] if content else 'NO CONTENT'}")
                print(f"    [DEBUG] Metadata keys: {list(meta.keys()) if meta else 'NO METADATA'}")
            
            # Extraction des informations de document (retriever format priority)
            document_name = (
                meta.get('document_name') or 
                chunk.get('document_name') or
                meta.get('document_id') or 
                'Document inconnu'
            )
            
            # Extraction des informations de page (retriever format priority)
            pages = []
            if meta.get('page_number'):
                # Format retriever standard
                pages = [meta['page_number']]
            elif meta.get('page_numbers_str'):
                # Format Late Chunker avec pages multiples
                pages = [int(p) for p in meta['page_numbers_str'].split(',') if p.strip()]
            elif meta.get('page_no'):
                pages = [meta['page_no']]
            elif chunk.get('page_numbers'):
                pages = chunk['page_numbers']
            
            page = pages[0] if pages else None
            
            # Extraction du code de réglementation (retriever format priority)
            regulation_code = (
                meta.get('regulation_code') or
                chunk.get('regulation_code') or
                'Code inconnu'
            )
            
            # Extraction du chemin du document source
            doc_source = meta.get("document_source", "") or chunk.get('document_source', '')
            
            # Construction du lien file:// (URL-encodée)
            import urllib.parse
            source_link = None
            if doc_source:
                # Remplace les backslashes par des slashes pour compatibilité URL
                doc_source_url = doc_source.replace('\\', '/')
                # Encode les espaces et caractères spéciaux
                doc_source_url = urllib.parse.quote(doc_source_url)
                if page:
                    source_link = f"file:///{doc_source_url}#page={page}"
                else:
                    source_link = f"file:///{doc_source_url}"
            
            # Hash du contenu pour la mise en surbrillance
            import hashlib
            content_hash = hashlib.md5(content.encode('utf-8', errors='ignore')).hexdigest()[:16]
            
            source_info = {
                'id': i + 1,
                'content': content,
                'document_name': document_name,
                'page': page,
                'pages': pages,
                'regulation_code': regulation_code,
                'source_link': source_link,
                'content_hash': content_hash,
                'relevance_score': chunk.get('score', 0.0)
            }
            
            sources.append(source_info)
        
        return sources
    
    def _update_stats(self, processing_time, success):
        """Met à jour les statistiques."""
        self.stats["queries_processed"] += 1
        self.stats["total_processing_time"] += processing_time
        if not success:
            self.stats["errors"] += 1
    
    # Méthodes de compatibilité
    def get_routing_info(self, query: str) -> Dict[str, Any]:
        """Informations de routage."""
        return self.master_routing_service.get_execution_plan(query)
    
    def explain_routing_decision(self, query: str) -> str:
        """Explication du routage."""
        return self.master_routing_service.explain_routing_decision(query)
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Statistiques de conversation."""
        return {
            **self.stats,
            "memory_stats": self.memory_service.get_stats() if self.memory_service else {}
        }
    
    def clear_conversation_memory(self) -> None:
        """Vide la mémoire."""
        if self.memory_service:
            self.memory_service.clear()
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """Statistiques des agents."""
        return {
            "workflow_type": self.workflow_type,
            "agents_initialized": self.agents_status,
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
    
    @property
    def conversation_memory(self):
        """Accès à la mémoire."""
        return self.memory_service