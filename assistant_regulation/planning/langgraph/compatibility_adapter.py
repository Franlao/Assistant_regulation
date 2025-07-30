"""
Compatibility Adapter for LangGraph Migration
=============================================

Adaptateur de compatibilité pour faciliter la migration progressive
du ModularOrchestrator vers LangGraphOrchestrator.
"""

from typing import Dict, Any, Optional, Generator
from .orchestrator import LangGraphOrchestrator
from ..sync.modular_orchestrator import ModularOrchestrator


class LangGraphCompatibilityAdapter:
    """
    Adaptateur permettant de remplacer ModularOrchestrator par LangGraphOrchestrator
    avec une interface 100% compatible.
    
    Cet adaptateur permet une migration progressive sans changer le code client.
    """
    
    def __init__(
        self,
        *,
        llm_provider: str = "ollama",
        model_name: str = "llama3.2",
        enable_verification: bool = True,
        workflow_type: str = "full",
        enable_debug: bool = False,
        fallback_to_modular: bool = True,
        # Tous les arguments du ModularOrchestrator
        **kwargs
    ):
        """
        Initialise l'adaptateur de compatibilité.
        
        Args:
            llm_provider: Fournisseur LLM
            model_name: Nom du modèle
            enable_verification: Activer la vérification
            workflow_type: Type de workflow LangGraph
            enable_debug: Mode debug
            fallback_to_modular: Utiliser ModularOrchestrator en fallback
            **kwargs: Arguments pour ModularOrchestrator
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.enable_verification = enable_verification
        self.fallback_to_modular = fallback_to_modular
        
        # Initialiser LangGraphOrchestrator
        try:
            self.langgraph_orchestrator = LangGraphOrchestrator(
                llm_provider=llm_provider,
                model_name=model_name,
                enable_verification=enable_verification,
                workflow_type=workflow_type,
                enable_debug=enable_debug
            )
            self.langgraph_available = True
            
        except Exception as e:
            print(f"Warning: LangGraph initialization failed: {e}")
            self.langgraph_available = False
            
        # Initialiser ModularOrchestrator en fallback
        if fallback_to_modular:
            try:
                self.modular_orchestrator = ModularOrchestrator(
                    llm_provider=llm_provider,
                    model_name=model_name,
                    enable_verification=enable_verification,
                    **kwargs
                )
                self.modular_available = True
                
            except Exception as e:
                print(f"Warning: ModularOrchestrator initialization failed: {e}")
                self.modular_available = False
        else:
            self.modular_orchestrator = None
            self.modular_available = False
    
    def process_query(
        self,
        query: str,
        *,
        use_images: bool = True,
        use_tables: bool = True,
        top_k: int = 5,
        use_conversation_context: bool = True,
        use_advanced_routing: bool = True,
        force_langgraph: bool = False,
        force_modular: bool = False,
    ) -> Dict[str, Any]:
        """
        Traite une requête avec interface compatible ModularOrchestrator.
        
        Args:
            query: Question de l'utilisateur
            use_images: Inclure les images
            use_tables: Inclure les tableaux
            top_k: Nombre de résultats
            use_conversation_context: Contexte conversationnel
            use_advanced_routing: Routage avancé
            force_langgraph: Forcer l'utilisation de LangGraph
            force_modular: Forcer l'utilisation de ModularOrchestrator
            
        Returns:
            Réponse au format ModularOrchestrator
        """
        # Déterminer quel orchestrateur utiliser
        use_langgraph = self._should_use_langgraph(force_langgraph, force_modular)
        
        if use_langgraph and self.langgraph_available:
            try:
                # Utiliser LangGraph
                result = self.langgraph_orchestrator.process_query(
                    query=query,
                    use_images=use_images,
                    use_tables=use_tables,
                    top_k=top_k,
                    use_conversation_context=use_conversation_context,
                    use_advanced_routing=use_advanced_routing
                )
                
                # Ajouter un indicateur du moteur utilisé
                result["metadata"]["orchestrator"] = "langgraph"
                return result
                
            except Exception as e:
                print(f"LangGraph failed, falling back to modular: {e}")
                # Fallback vers modular si LangGraph échoue
                if self.modular_available:
                    return self._process_with_modular(
                        query, use_images, use_tables, top_k,
                        use_conversation_context, use_advanced_routing
                    )
                else:
                    raise e
        
        elif self.modular_available:
            # Utiliser ModularOrchestrator
            return self._process_with_modular(
                query, use_images, use_tables, top_k,
                use_conversation_context, use_advanced_routing
            )
        
        else:
            raise RuntimeError("Aucun orchestrateur disponible")
    
    def process_query_stream(
        self,
        query: str,
        *,
        use_images: bool = True,
        use_tables: bool = True,
        top_k: int = 5,
        use_conversation_context: bool = True,
        use_advanced_routing: bool = True,
        force_langgraph: bool = False,
        force_modular: bool = False,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Traite une requête en streaming avec interface compatible.
        
        Args:
            query: Question de l'utilisateur
            **kwargs: Paramètres de traitement
            
        Yields:
            Événements de streaming
        """
        use_langgraph = self._should_use_langgraph(force_langgraph, force_modular)
        
        if use_langgraph and self.langgraph_available:
            try:
                # Streaming LangGraph
                yield from self.langgraph_orchestrator.process_query_stream(
                    query=query,
                    use_images=use_images,
                    use_tables=use_tables,
                    top_k=top_k,
                    use_conversation_context=use_conversation_context,
                    use_advanced_routing=use_advanced_routing
                )
                
            except Exception as e:
                # Fallback vers modular streaming
                if self.modular_available:
                    yield from self._process_stream_with_modular(
                        query, use_images, use_tables, top_k
                    )
                else:
                    yield {"type": "error", "message": f"Streaming failed: {e}"}
        
        elif self.modular_available:
            # Streaming modular
            yield from self._process_stream_with_modular(
                query, use_images, use_tables, top_k
            )
        
        else:
            yield {"type": "error", "message": "Aucun orchestrateur disponible"}
    
    def _should_use_langgraph(self, force_langgraph: bool, force_modular: bool) -> bool:
        """
        Détermine quel orchestrateur utiliser.
        
        Args:
            force_langgraph: Forcer LangGraph
            force_modular: Forcer ModularOrchestrator
            
        Returns:
            True si utiliser LangGraph
        """
        if force_langgraph and self.langgraph_available:
            return True
        if force_modular and self.modular_available:
            return False
        
        # Par défaut, préférer LangGraph s'il est disponible
        return self.langgraph_available
    
    def _process_with_modular(
        self,
        query: str,
        use_images: bool,
        use_tables: bool,
        top_k: int,
        use_conversation_context: bool,
        use_advanced_routing: bool
    ) -> Dict[str, Any]:
        """Traite avec ModularOrchestrator."""
        result = self.modular_orchestrator.process_query(
            query=query,
            use_images=use_images,
            use_tables=use_tables,
            top_k=top_k,
            use_conversation_context=use_conversation_context,
            use_advanced_routing=use_advanced_routing
        )
        
        # Ajouter l'indicateur d'orchestrateur
        if "metadata" not in result:
            result["metadata"] = {}
        result["metadata"]["orchestrator"] = "modular"
        
        return result
    
    def _process_stream_with_modular(
        self,
        query: str,
        use_images: bool,
        use_tables: bool,
        top_k: int
    ) -> Generator[Dict[str, Any], None, None]:
        """Traite en streaming avec ModularOrchestrator."""
        yield from self.modular_orchestrator.process_query_stream(
            query=query,
            use_images=use_images,
            use_tables=use_tables,
            top_k=top_k
        )
    
    # ------------------------------------------------------------------
    # Méthodes de compatibilité complète avec ModularOrchestrator
    # ------------------------------------------------------------------
    
    def get_routing_info(self, query: str) -> Dict[str, Any]:
        """Compatible avec ModularOrchestrator.get_routing_info()."""
        if self.langgraph_available:
            return self.langgraph_orchestrator.get_routing_info(query)
        elif self.modular_available:
            return self.modular_orchestrator.get_routing_info(query)
        else:
            return {}
    
    def explain_routing_decision(self, query: str) -> str:
        """Compatible avec ModularOrchestrator.explain_routing_decision()."""
        if self.langgraph_available:
            return self.langgraph_orchestrator.explain_routing_decision(query)
        elif self.modular_available:
            return self.modular_orchestrator.explain_routing_decision(query)
        else:
            return "Aucun orchestrateur disponible"
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Compatible avec ModularOrchestrator.get_conversation_stats()."""
        stats = {"orchestrator_status": {
            "langgraph_available": self.langgraph_available,
            "modular_available": self.modular_available
        }}
        
        if self.langgraph_available:
            stats.update(self.langgraph_orchestrator.get_conversation_stats())
        elif self.modular_available:
            stats.update(self.modular_orchestrator.get_conversation_stats())
            
        return stats
    
    def clear_conversation_memory(self) -> None:
        """Compatible avec ModularOrchestrator.clear_conversation_memory()."""
        if self.langgraph_available:
            self.langgraph_orchestrator.clear_conversation_memory()
        if self.modular_available:
            self.modular_orchestrator.clear_conversation_memory()
    
    @property
    def conversation_memory(self):
        """Compatible avec ModularOrchestrator.conversation_memory."""
        if self.langgraph_available:
            return self.langgraph_orchestrator.conversation_memory
        elif self.modular_available:
            return self.modular_orchestrator.conversation_memory
        else:
            return None
    
    # Propriétés compatibles
    @property
    def llm_provider(self) -> str:
        return self._llm_provider
    
    @llm_provider.setter
    def llm_provider(self, value: str):
        self._llm_provider = value
        # Propager aux orchestrateurs si nécessaire
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    @model_name.setter
    def model_name(self, value: str):
        self._model_name = value
    
    # Méthodes de diagnostic
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Retourne le statut des orchestrateurs."""
        return {
            "langgraph": {
                "available": self.langgraph_available,
                "workflow_type": self.langgraph_orchestrator.workflow_type if self.langgraph_available else None
            },
            "modular": {
                "available": self.modular_available
            },
            "active_orchestrator": "langgraph" if (self.langgraph_available and not self.fallback_to_modular) else "modular"
        }
    
    def switch_to_langgraph(self) -> bool:
        """Force l'utilisation de LangGraph."""
        if self.langgraph_available:
            self.fallback_to_modular = False
            return True
        return False
    
    def switch_to_modular(self) -> bool:
        """Force l'utilisation de ModularOrchestrator."""
        if self.modular_available:
            self.fallback_to_modular = True
            return True
        return False
    
    def run_comparison_test(self, query: str) -> Dict[str, Any]:
        """
        Exécute la même requête sur les deux orchestrateurs pour comparaison.
        
        Args:
            query: Question de test
            
        Returns:
            Résultats comparatifs
        """
        results = {"query": query, "results": {}}
        
        # Test LangGraph
        if self.langgraph_available:
            try:
                start_time = __import__("time").time()
                langgraph_result = self.langgraph_orchestrator.process_query(query)
                langgraph_time = __import__("time").time() - start_time
                
                results["results"]["langgraph"] = {
                    "success": True,
                    "processing_time": langgraph_time,
                    "answer_length": len(langgraph_result.get("answer", "")),
                    "sources_count": len(langgraph_result.get("sources", [])),
                    "error": None
                }
            except Exception as e:
                results["results"]["langgraph"] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Test ModularOrchestrator
        if self.modular_available:
            try:
                start_time = __import__("time").time()
                modular_result = self.modular_orchestrator.process_query(query)
                modular_time = __import__("time").time() - start_time
                
                results["results"]["modular"] = {
                    "success": True,
                    "processing_time": modular_time,
                    "answer_length": len(modular_result.get("answer", "")),
                    "sources_count": len(modular_result.get("sources", [])),
                    "error": None
                }
            except Exception as e:
                results["results"]["modular"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results