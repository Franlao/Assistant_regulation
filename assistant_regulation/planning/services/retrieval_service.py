from typing import Dict, Optional, List, Any
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from functools import partial
import asyncio
from dataclasses import dataclass

from assistant_regulation.processing.Modul_emb.TextRetriever import SimpleTextRetriever
from assistant_regulation.processing.Modul_emb.ImageRetriever import ImageRetriever
from assistant_regulation.processing.Modul_emb.TableRetriever import TableRetriever
from assistant_regulation.planning.sync.lang_py import translate_query


@dataclass
class RetrievalConfig:
    """Configuration pour la parallélisation du RetrievalService."""
    max_workers: int = 16
    timeout_seconds: float = 30.0
    retry_attempts: int = 2
    enable_caching: bool = True
    enable_detailed_logging: bool = False


class RetrievalService:
    """Centralise la recherche dans les différentes bases (texte, image, tableau).

    Cette couche optimisée offre :
    - Parallélisation avancée avec gestion d'erreurs robuste
    - Système de retry automatique
    - Timeouts configurables
    - Métriques et logging détaillé
    - Support pour différents modes de parallélisation
    """

    def __init__(
        self,
        text_retriever: Optional[SimpleTextRetriever] = None,
        image_retriever: Optional[ImageRetriever] = None,
        table_retriever: Optional[TableRetriever] = None,
        config: Optional[RetrievalConfig] = None,
    ) -> None:
        self.text_retriever = text_retriever or SimpleTextRetriever()
        self.image_retriever = image_retriever or ImageRetriever()
        self.table_retriever = table_retriever or TableRetriever()
        self.config = config or RetrievalConfig()
        
        # Logging setup
        self.logger = logging.getLogger(__name__)
        
        # Métriques de performance
        self.retrieval_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_latency": 0.0,
            "parallel_efficiency": 0.0
        }

    # ---------------------------------------------------------------------
    # API public optimisée
    # ---------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        *,
        use_images: bool = True,
        use_tables: bool = True,
        top_k: int = 5,
        mode: str = "optimized",  # "optimized", "fast", "robust"
    ) -> Dict:
        """Retourne un dictionnaire {text, images, tables} avec parallélisation optimisée.

        Args:
            query: Requête de recherche
            use_images: Inclure la recherche d'images
            use_tables: Inclure la recherche de tableaux
            top_k: Nombre de résultats par source
            mode: Mode de parallélisation ("optimized", "fast", "robust")
            
        Returns:
            Dict avec les résultats de recherche par source
        """
        start_time = time.time()
        self.retrieval_stats["total_calls"] += 1
        
        try:
            if mode == "optimized":
                results = self._retrieve_optimized(query, use_images, use_tables, top_k)
            elif mode == "fast":
                results = self._retrieve_fast(query, use_images, use_tables, top_k)
            elif mode == "robust":
                results = self._retrieve_robust(query, use_images, use_tables, top_k)
            else:
                raise ValueError(f"Mode '{mode}' non supporté. Utilisez: optimized, fast, robust")
            
            # Mise à jour des métriques
            elapsed = time.time() - start_time
            self._update_stats(elapsed, success=True)
            
            if self.config.enable_detailed_logging:
                self.logger.info(f"Recherche réussie en {elapsed:.2f}s - Mode: {mode}")
            
            return results
            
        except Exception as e:
            elapsed = time.time() - start_time
            self._update_stats(elapsed, success=False)
            self.logger.error(f"Erreur lors de la recherche: {e}")
            return {"text": [], "images": [], "tables": []}
    
    def _retrieve_optimized(self, query: str, use_images: bool, use_tables: bool, top_k: int) -> Dict:
        """Mode optimisé avec gestion d'erreurs avancée et retry."""
        query_en = translate_query(query=query)
        
        # Préparer les tâches avec priorités
        task_configs = []
        
        # Texte (priorité haute - toujours nécessaire)
        task_configs.append({
            "name": "text",
            "func": self.text_retriever.search_with_context,
            "args": (query_en,),
            "kwargs": {"top_k": top_k},
            "priority": 1,
            "timeout": self.config.timeout_seconds
        })
        
        # Images (priorité moyenne)
        if use_images:
            task_configs.append({
                "name": "images",
                "func": self.image_retriever.search,
                "args": (query,),
                "kwargs": {"top_k": max(1, top_k // 2)},
                "priority": 2,
                "timeout": self.config.timeout_seconds * 1.5  # Plus de temps pour les images
            })
        
        # Tables (priorité basse)
        if use_tables:
            task_configs.append({
                "name": "tables",
                "func": self.table_retriever.search,
                "args": (query_en,),
                "kwargs": {"top_k": min(3, top_k)},
                "priority": 3,
                "timeout": self.config.timeout_seconds
            })
        
        return self._execute_parallel_with_retry(task_configs)
    
    def _retrieve_fast(self, query: str, use_images: bool, use_tables: bool, top_k: int) -> Dict:
        """Mode rapide avec timeouts réduits et moins de retry."""
        query_en = translate_query(query=query)
        
        task_configs = []
        fast_timeout = self.config.timeout_seconds * 0.5
        
        task_configs.append({
            "name": "text",
            "func": self.text_retriever.search_with_context,
            "args": (query_en,),
            "kwargs": {"top_k": min(top_k, 3)},  # Réduire top_k pour la vitesse
            "priority": 1,
            "timeout": fast_timeout
        })
        
        if use_images:
            task_configs.append({
                "name": "images",
                "func": self.image_retriever.search,
                "args": (query,),
                "kwargs": {"top_k": max(1, top_k // 3)},
                "priority": 2,
                "timeout": fast_timeout
            })
        
        if use_tables:
            task_configs.append({
                "name": "tables",
                "func": self.table_retriever.search,
                "args": (query_en,),
                "kwargs": {"top_k": 2},
                "priority": 3,
                "timeout": fast_timeout
            })
        
        return self._execute_parallel_simple(task_configs)
    
    def _retrieve_robust(self, query: str, use_images: bool, use_tables: bool, top_k: int) -> Dict:
        """Mode robuste avec retry multiple et fallback."""
        query_en = translate_query(query=query)
        
        task_configs = []
        robust_timeout = self.config.timeout_seconds * 2.0
        
        task_configs.append({
            "name": "text",
            "func": self.text_retriever.search_with_context,
            "args": (query_en,),
            "kwargs": {"top_k": top_k},
            "priority": 1,
            "timeout": robust_timeout,
            "max_retries": self.config.retry_attempts * 2
        })
        
        if use_images:
            task_configs.append({
                "name": "images",
                "func": self.image_retriever.search,
                "args": (query,),
                "kwargs": {"top_k": max(1, top_k // 2)},
                "priority": 2,
                "timeout": robust_timeout,
                "max_retries": self.config.retry_attempts
            })
        
        if use_tables:
            task_configs.append({
                "name": "tables",
                "func": self.table_retriever.search,
                "args": (query_en,),
                "kwargs": {"top_k": min(3, top_k)},
                "priority": 3,
                "timeout": robust_timeout,
                "max_retries": self.config.retry_attempts
            })
        
        return self._execute_parallel_with_retry(task_configs, robust_mode=True)
    
    def _execute_parallel_with_retry(self, task_configs: List[Dict], robust_mode: bool = False) -> Dict:
        """Exécution parallèle avec retry et gestion d'erreurs avancée."""
        results = {"text": [], "images": [], "tables": []}
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Soumettre toutes les tâches
            future_to_task = {}
            
            for task_config in task_configs:
                future = executor.submit(
                    self._execute_task_with_retry,
                    task_config
                )
                future_to_task[future] = task_config
            
            # Collecter les résultats avec gestion des timeouts
            for future in as_completed(future_to_task, timeout=self.config.timeout_seconds * 2):
                task_config = future_to_task[future]
                task_name = task_config["name"]
                
                try:
                    result = future.result(timeout=task_config.get("timeout", self.config.timeout_seconds))
                    results[task_name] = result if result is not None else []
                    
                    if self.config.enable_detailed_logging:
                        self.logger.info(f"Tâche '{task_name}' réussie: {len(results[task_name])} résultats")
                        
                except Exception as e:
                    self.logger.warning(f"Tâche '{task_name}' échouée: {e}")
                    results[task_name] = []
                    
                    # En mode robuste, essayer un fallback
                    if robust_mode and task_name == "text":
                        try:
                            fallback_result = self._fallback_text_search(task_config)
                            results[task_name] = fallback_result
                            self.logger.info(f"Fallback réussi pour '{task_name}'")
                        except Exception as fallback_error:
                            self.logger.error(f"Fallback échoué pour '{task_name}': {fallback_error}")
        
        return results
    
    def _execute_parallel_simple(self, task_configs: List[Dict]) -> Dict:
        """Exécution parallèle simple pour le mode rapide."""
        results = {"text": [], "images": [], "tables": []}
        
        with ThreadPoolExecutor(max_workers=min(self.config.max_workers, len(task_configs))) as executor:
            future_to_name = {}
            
            for task_config in task_configs:
                func = task_config["func"]
                args = task_config["args"]
                kwargs = task_config["kwargs"]
                
                future = executor.submit(func, *args, **kwargs)
                future_to_name[future] = task_config["name"]
            
            for future in as_completed(future_to_name, timeout=self.config.timeout_seconds):
                task_name = future_to_name[future]
                try:
                    result = future.result(timeout=self.config.timeout_seconds * 0.5)
                    results[task_name] = result if result is not None else []
                except Exception as e:
                    if self.config.enable_detailed_logging:
                        self.logger.warning(f"Tâche rapide '{task_name}' échouée: {e}")
                    results[task_name] = []
        
        return results
    
    def _execute_task_with_retry(self, task_config: Dict) -> Any:
        """Exécute une tâche avec retry automatique."""
        func = task_config["func"]
        args = task_config["args"]
        kwargs = task_config["kwargs"]
        max_retries = task_config.get("max_retries", self.config.retry_attempts)
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = 0.5 * (2 ** attempt)  # Backoff exponentiel
                    if self.config.enable_detailed_logging:
                        self.logger.warning(f"Tentative {attempt + 1} échouée, retry dans {wait_time}s")
                    time.sleep(wait_time)
                    continue
                break
        
        raise last_exception
    
    def _fallback_text_search(self, task_config: Dict) -> List:
        """Recherche de fallback pour le texte avec paramètres réduits."""
        try:
            # Essayer avec des paramètres réduits
            reduced_top_k = max(1, task_config["kwargs"]["top_k"] // 2)
            return self.text_retriever.search_with_context(
                *task_config["args"], 
                top_k=reduced_top_k
            )
        except Exception:
            # Dernière tentative avec recherche basique
            return self.text_retriever.search_with_context(
                *task_config["args"], 
                top_k=1
            )
    
    def _update_stats(self, elapsed_time: float, success: bool) -> None:
        """Met à jour les statistiques de performance."""
        if success:
            self.retrieval_stats["successful_calls"] += 1
        else:
            self.retrieval_stats["failed_calls"] += 1
        
        # Mise à jour de la latence moyenne
        total_successful = self.retrieval_stats["successful_calls"]
        if total_successful > 0:
            current_avg = self.retrieval_stats["average_latency"]
            self.retrieval_stats["average_latency"] = (
                (current_avg * (total_successful - 1) + elapsed_time) / total_successful
            )
    
    def get_performance_stats(self) -> Dict:
        """Retourne les statistiques de performance du service."""
        total_calls = self.retrieval_stats["total_calls"]
        if total_calls == 0:
            return {"status": "no_calls_yet"}
        
        success_rate = (self.retrieval_stats["successful_calls"] / total_calls) * 100
        
        return {
            "total_calls": total_calls,
            "successful_calls": self.retrieval_stats["successful_calls"],
            "failed_calls": self.retrieval_stats["failed_calls"],
            "success_rate_percent": round(success_rate, 2),
            "average_latency_seconds": round(self.retrieval_stats["average_latency"], 3),
            "config": {
                "max_workers": self.config.max_workers,
                "timeout_seconds": self.config.timeout_seconds,
                "retry_attempts": self.config.retry_attempts
            }
        }
    
    def reset_stats(self) -> None:
        """Remet à zéro les statistiques de performance."""
        self.retrieval_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_latency": 0.0,
            "parallel_efficiency": 0.0
        } 

    # ---------------------------------------------------------------------
    # Délégation des méthodes avancées de BaseRetriever
    # ---------------------------------------------------------------------
    def search_by_regulation(self, regulation_code: str, query: str, top_k: int = 10, search_type: str = 'hybrid', alpha: float = 0.7):
        return self.text_retriever.search_by_regulation(regulation_code, query, top_k, search_type, alpha)

    def get_all_chunks_for_regulation(self, regulation_code: str):
        return self.text_retriever.get_all_chunks_for_regulation(regulation_code)

    def get_available_regulations(self):
        return self.text_retriever.get_available_regulations()

    def get_regulation_stats(self, regulation_code: str):
        return self.text_retriever.get_regulation_stats(regulation_code)

    def search_multiple_regulations(self, regulation_codes, query, top_k = 5, search_type = 'hybrid'):
        return self.text_retriever.search_multiple_regulations(regulation_codes, query, top_k, search_type)

    def compare_regulations(self, regulation_codes, query, top_k = 5):
        return self.text_retriever.compare_regulations(regulation_codes, query, top_k)

    def get_regulation_intersection(self, regulation_codes, query):
        return self.text_retriever.get_regulation_intersection(regulation_codes, query) 