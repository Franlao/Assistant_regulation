from typing import Dict, Optional, List, Any
import logging
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from functools import partial, lru_cache
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

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
    cache_ttl_minutes: int = 10
    cache_max_size: int = 100


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
            "parallel_efficiency": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }

        # Cache intelligent avec TTL
        self._result_cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

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

        # Vérifier le cache en premier
        if self.config.enable_caching:
            cache_key = self._generate_cache_key(query, use_images, use_tables, top_k, mode)
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                self.retrieval_stats["cache_hits"] += 1
                elapsed = time.time() - start_time
                self._update_stats(elapsed, success=True)
                # Log toujours les cache hits pour monitoring
                print(f"[CACHE HIT] {elapsed:.3f}s - Query: '{query[:50]}...' - Key: {cache_key[:12]}...")
                self.logger.info(f"CACHE HIT en {elapsed:.3f}s - Query: '{query[:50]}...' - Key: {cache_key[:12]}...")
                return cached_result
            else:
                self.retrieval_stats["cache_misses"] += 1
                # Log les cache misses pour monitoring
                print(f"[CACHE MISS] Query: '{query[:50]}...' - Key: {cache_key[:12]}...")
                self.logger.info(f"CACHE MISS - Query: '{query[:50]}...' - Key: {cache_key[:12]}...")

        try:
            if mode == "optimized":
                results = self._retrieve_optimized(query, use_images, use_tables, top_k)
            elif mode == "fast":
                results = self._retrieve_fast(query, use_images, use_tables, top_k)
            elif mode == "robust":
                results = self._retrieve_robust(query, use_images, use_tables, top_k)
            else:
                raise ValueError(f"Mode '{mode}' non supporté. Utilisez: optimized, fast, robust")

            # Mettre en cache le résultat
            if self.config.enable_caching:
                self._store_in_cache(cache_key, results)
                print(f"[CACHE STORE] Query: '{query[:50]}...' - Key: {cache_key[:12]}...")
                self.logger.info(f"CACHE STORE - Query: '{query[:50]}...' - Key: {cache_key[:12]}...")

            # Mise à jour des métriques
            elapsed = time.time() - start_time
            self._update_stats(elapsed, success=True)

            total_results = sum(len(results.get(k, [])) for k in ["text", "images", "tables"])
            cache_status = "MISS" if self.config.enable_caching else "DISABLED"
            print(f"[RETRIEVAL] {elapsed:.2f}s - Mode: {mode} - Cache: {cache_status} - Results: {total_results}")
            self.logger.info(f"RETRIEVAL COMPLETE en {elapsed:.2f}s - Mode: {mode} - Cache: {cache_status} - Results: {total_results}")

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

    # ---------------------------------------------------------------------
    # Cache intelligent avec TTL
    # ---------------------------------------------------------------------
    def _generate_cache_key(self, query: str, use_images: bool, use_tables: bool, top_k: int, mode: str) -> str:
        """Génère une clé de cache basée sur les paramètres de la requête."""
        # Normaliser la requête pour éviter les variations mineures
        normalized_query = query.lower().strip()

        # Créer un hash des paramètres
        params_str = f"{normalized_query}|{use_images}|{use_tables}|{top_k}|{mode}"
        return hashlib.md5(params_str.encode('utf-8')).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Récupère un résultat du cache s'il est valide (non expiré)."""
        if cache_key not in self._result_cache:
            return None

        # Vérifier l'expiration
        cache_time = self._cache_timestamps.get(cache_key)
        if cache_time is None:
            return None

        ttl_delta = timedelta(minutes=self.config.cache_ttl_minutes)
        if datetime.now() - cache_time > ttl_delta:
            # Entrée expirée, la supprimer
            self._remove_from_cache(cache_key)
            return None

        return self._result_cache[cache_key].copy()  # Copie pour éviter les modifications

    def _store_in_cache(self, cache_key: str, results: Dict) -> None:
        """Stocke un résultat dans le cache avec gestion de la taille maximale."""
        # Nettoyer les entrées expirées si nécessaire
        self._cleanup_expired_cache_entries()

        # Si le cache est plein, supprimer les entrées les plus anciennes
        if len(self._result_cache) >= self.config.cache_max_size:
            self._evict_oldest_cache_entries(self.config.cache_max_size // 4)  # Supprimer 25%

        # Stocker la nouvelle entrée
        self._result_cache[cache_key] = results.copy()  # Copie pour éviter les modifications
        self._cache_timestamps[cache_key] = datetime.now()

        if self.config.enable_detailed_logging:
            self.logger.debug(f"Cache STORE - Key: {cache_key[:20]}... - Size: {len(self._result_cache)}")

    def _remove_from_cache(self, cache_key: str) -> None:
        """Supprime une entrée du cache."""
        self._result_cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)

    def _cleanup_expired_cache_entries(self) -> None:
        """Nettoie les entrées de cache expirées."""
        now = datetime.now()
        ttl_delta = timedelta(minutes=self.config.cache_ttl_minutes)

        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if now - timestamp > ttl_delta
        ]

        for key in expired_keys:
            self._remove_from_cache(key)

        if self.config.enable_detailed_logging and expired_keys:
            self.logger.debug(f"Cache CLEANUP - Supprimé {len(expired_keys)} entrées expirées")

    def _evict_oldest_cache_entries(self, count: int) -> None:
        """Supprime les entrées de cache les plus anciennes."""
        if not self._cache_timestamps:
            return

        # Trier par timestamp croissant (plus ancien en premier)
        sorted_entries = sorted(self._cache_timestamps.items(), key=lambda x: x[1])

        for i in range(min(count, len(sorted_entries))):
            key_to_remove = sorted_entries[i][0]
            self._remove_from_cache(key_to_remove)

        if self.config.enable_detailed_logging:
            self.logger.debug(f"Cache EVICT - Supprimé {min(count, len(sorted_entries))} anciennes entrées")

    def clear_cache(self) -> None:
        """Vide complètement le cache."""
        entries_count = len(self._result_cache)
        self._result_cache.clear()
        self._cache_timestamps.clear()

        if self.config.enable_detailed_logging:
            self.logger.info(f"Cache CLEAR - Supprimé {entries_count} entrées")

    def get_cache_stats(self) -> Dict:
        """Retourne les statistiques du cache."""
        return {
            "cache_size": len(self._result_cache),
            "cache_max_size": self.config.cache_max_size,
            "cache_ttl_minutes": self.config.cache_ttl_minutes,
            "cache_hits": self.retrieval_stats["cache_hits"],
            "cache_misses": self.retrieval_stats["cache_misses"],
            "hit_rate_percent": (
                round((self.retrieval_stats["cache_hits"] /
                      (self.retrieval_stats["cache_hits"] + self.retrieval_stats["cache_misses"]) * 100), 2)
                if (self.retrieval_stats["cache_hits"] + self.retrieval_stats["cache_misses"]) > 0 else 0.0
            )
        }

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
        
        cache_stats = self.get_cache_stats() if self.config.enable_caching else {"cache_disabled": True}

        return {
            "total_calls": total_calls,
            "successful_calls": self.retrieval_stats["successful_calls"],
            "failed_calls": self.retrieval_stats["failed_calls"],
            "success_rate_percent": round(success_rate, 2),
            "average_latency_seconds": round(self.retrieval_stats["average_latency"], 3),
            "cache_stats": cache_stats,
            "config": {
                "max_workers": self.config.max_workers,
                "timeout_seconds": self.config.timeout_seconds,
                "retry_attempts": self.config.retry_attempts,
                "caching_enabled": self.config.enable_caching
            }
        }
    
    def reset_stats(self) -> None:
        """Remet à zéro les statistiques de performance."""
        self.retrieval_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_latency": 0.0,
            "parallel_efficiency": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        } 

    # ---------------------------------------------------------------------
    # Délégation des méthodes avancées de BaseRetriever
    # ---------------------------------------------------------------------
    def search_by_regulation(self, regulation_code: str, query: str, top_k: int = 10, search_type: str = 'hybrid', alpha: float = 0.7):
        if self.config.enable_caching:
            # Créer une clé de cache pour cette méthode spécialisée
            cache_key = self._generate_cache_key(f"by_reg_{regulation_code}_{query}", False, False, top_k, search_type)
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                print(f"[CACHE HIT SPECIALIZED] search_by_regulation - Query: '{query[:30]}...' - Reg: {regulation_code}")
                return cached_result
            else:
                print(f"[CACHE MISS SPECIALIZED] search_by_regulation - Query: '{query[:30]}...' - Reg: {regulation_code}")

        result = self.text_retriever.search_by_regulation(regulation_code, query, top_k, search_type, alpha)

        if self.config.enable_caching:
            self._store_in_cache(cache_key, result)
            print(f"[CACHE STORE SPECIALIZED] search_by_regulation - Key: {cache_key[:12]}...")

        return result

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