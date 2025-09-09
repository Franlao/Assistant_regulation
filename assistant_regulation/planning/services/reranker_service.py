from __future__ import annotations

from typing import List, Dict, Any
import time

import requests  # Appel HTTP à l'API Jina
from config.config import get_config


# Optionnel : installation requise
# pip install FlagEmbedding jinaai>=0.5 colbert-ai "torch>=2.2" transformers

try:
    from colbert import Searcher  # ColBERT-v2
except ImportError:  # pragma: no cover
    Searcher = None  # type: ignore


class RerankerService:
    """Service de reranking basé uniquement sur l'API HTTP Jina.

    Exemple d'utilisation :
        reranker = RerankerService()
        best_chunks = reranker.rerank_chunks(query, chunks)
    """

    def __init__(self, model_name: str | None = None):
        import os
        cfg = get_config()
        
        # Détecter Railway et désactiver si configuré
        self.is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
        self.jina_enabled = cfg.jina.enabled and not (self.is_railway and cfg.jina.disable_on_railway)
        
        if not self.jina_enabled:
            print("Jina reranking désactivé (Railway détecté ou configuration)")
            self.api_key = None
            self.api_url = None
            self.model_name = None
            return
        
        self.api_key: str | None = cfg.get_jina_api_key()
        if not self.api_key:
            print("Warning: Clé API Jina introuvable, reranking désactivé")
            self.jina_enabled = False
            return

        self.api_url: str = cfg.jina.api_url
        self.model_name: str = model_name or cfg.jina.default_model
        self.timeout: int = cfg.jina.timeout
        self.max_retries: int = cfg.jina.max_retries
        self.retry_delay: float = cfg.jina.retry_delay

    # ------------------------------------------------------------------
    def _call_jina_api(self, query: str, docs: List[Any]) -> List[tuple[Any, float]]:
        """Envoie la requête POST à l'API Jina avec retry logic et renvoie la liste (doc, score)."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "query": query,
            "top_n": len(docs),
            "documents": docs,
            "return_documents": False,
        }
        
        last_error = None
        for attempt in range(self.max_retries + 1):  # +1 pour la première tentative
            try:
                # Utiliser timeout depuis config
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
                
                # Gestion spéciale pour les erreurs 503 (service indisponible)
                if response.status_code == 503:
                    raise requests.exceptions.RequestException(f"Service Jina temporairement indisponible (503)")
                
                if response.status_code >= 400:
                    raise RuntimeError(f"Jina API error {response.status_code}: {response.text}")
                
                data = response.json()
                
                # Si on arrive ici, la requête a réussi
                break
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"RETRY: Tentative Jina {attempt + 1}/{self.max_retries + 1} échouée: {type(e).__name__}. Nouvel essai dans {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Dernière tentative échouée
                    raise RuntimeError(f"Jina rerank failed after {self.max_retries + 1} attempts: {last_error}")
            except Exception as e:
                # Pour les autres erreurs (non réseau), ne pas faire de retry
                raise RuntimeError(f"Jina API error: {e}")
        else:
            # Cette ligne ne devrait jamais être atteinte
            raise RuntimeError(f"Jina rerank failed after {self.max_retries + 1} attempts: {last_error}")

        # Le format de réponse peut varier légèrement selon la version de l'API.
        # On essaye donc plusieurs clés possibles.
        if "scores" in data and isinstance(data["scores"], list):
            # 'scores' est aligné sur l'ordre d'envoi des documents
            return list(zip(docs, data["scores"]))

        if "results" in data and isinstance(data["results"], list):
            pairs: List[tuple[Any, float]] = []
            for item in data["results"]:
                idx = item.get("index")
                score = item.get("relevance_score") or item.get("score")
                if isinstance(idx, int) and 0 <= idx < len(docs) and score is not None:
                    pairs.append((docs[idx], float(score)))
            return pairs

        raise ValueError(
            f"Champ de scores introuvable dans la réponse Jina : {list(data.keys())}"
        )

    # ------------------------------------------------------------------
    def rerank(self, query: str, docs: List[Any], top_k: int = 5):
        """Retourne une liste (doc, score) triée par pertinence décroissante."""
        if not docs:
            return []
        pairs = self._call_jina_api(query, docs)
        if isinstance(pairs[0], tuple):
            ranked = sorted(pairs, key=lambda x: x[1], reverse=True)
        else:  # fallback (ancienne logique)
            ranked = sorted(zip(docs, pairs), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    # ------------------------------------------------------------------
    def rerank_chunks(self, query: str, text_chunks: List[Dict], top_k: int = 5):
        """Rerank puis retourne la liste de chunks réordonnés."""
        if not text_chunks:
            return []
        
        # Si Jina désactivé, retourner les chunks dans l'ordre original
        if not self.jina_enabled:
            print("Reranking Jina désactivé, retour chunks originaux")
            return text_chunks[:top_k]

        index_to_chunk: List[Dict] = []
        docs: List[Any] = []

        for idx, chunk in enumerate(text_chunks):
            # Détection image
            meta = chunk.get("metadata", {}) if isinstance(chunk.get("metadata"), dict) else chunk.get("metadata", {})
            image_url = meta.get("image_url") if isinstance(meta, dict) else None
            if image_url:
                if image_url.startswith("http"):
                    doc = {"image": image_url}
                elif image_url.startswith("data:image") and "," in image_url:
                    b64 = image_url.split(",", 1)[1]
                    doc = {"bytes": b64}
                else:
                    image_url = None  # unsupported format
            else:
                text = chunk.get("content") or chunk.get("documents") or chunk.get("text") or ""
                if not text.strip():
                    continue  # skip chunks without usable content
                doc = {"text": text}

            docs.append(doc)
            index_to_chunk.append(chunk)

        if not docs:
            return []

        # Optimisation: limiter le nombre de documents pour éviter les timeouts
        # Si plus de 20 documents, prendre seulement les meilleurs premiers
        max_docs_for_rerank = 20
        if len(docs) > max_docs_for_rerank:
            print(f"OPTIMIZATION: Limitation à {max_docs_for_rerank} documents pour le reranking (sur {len(docs)} disponibles)")
            docs = docs[:max_docs_for_rerank]
            index_to_chunk = index_to_chunk[:max_docs_for_rerank]

        try:
            ranked_pairs = self.rerank(query, docs, top_k=top_k)
        except Exception as e:
            error_type = type(e).__name__
            error_str = str(e).lower()
            
            if "timeout" in error_str or "timed out" in error_str:
                print(f"WARNING: Jina rerank timeout après {self.timeout}s. Documents: {len(docs)}")
                print("SUGGESTION: Le service Jina met plus de temps que prévu à répondre")
            elif "503" in error_str or "service temporarily unavailable" in error_str:
                print(f"WARNING: Service Jina temporairement indisponible (erreur 503)")
                print("INFO: Jina AI est en maintenance ou surchargé. Réessayez dans quelques minutes")
                print("STATUS: Vérifiez https://status.jina.ai")
            elif "connection" in error_str or "dns" in error_str:
                print(f"ERROR: Problème de connexion Jina API: {error_type}")
                print("SUGGESTION: Vérifiez votre connexion internet et les paramètres de proxy")
            elif "401" in error_str or "unauthorized" in error_str:
                print(f"ERROR: Clé API Jina invalide ou expirée")
                print("SUGGESTION: Vérifiez votre clé API Jina dans la configuration")
            elif "429" in error_str or "rate limit" in error_str:
                print(f"WARNING: Limite de taux Jina atteinte")
                print("SUGGESTION: Vous avez atteint votre quota API. Attendez ou upgrader votre plan")
            else:
                print(f"ERROR: Erreur Jina rerank ({error_type}): {e}")
                print("DEBUG: Erreur inattendue - vérifiez les logs pour plus de détails")
            
            # Fallback: retourner les chunks dans l'ordre original avec scores par défaut
            print("FALLBACK: Basculement vers le mode sans reranking")
            for idx, chunk in enumerate(index_to_chunk):
                chunk["rerank_score"] = 1.0 - (idx * 0.05)  # Score décroissant plus subtil
                chunk["score"] = chunk.get("score", 0.5)  # Garder le score original ou défaut
            return index_to_chunk[:top_k]
        enriched_chunks: List[Dict] = []
        for doc, score in ranked_pairs:
            idx = docs.index(doc)
            chunk = index_to_chunk[idx]
            chunk["rerank_score"] = score
            # remplace score principal aussi pour affichage simple
            chunk["score"] = score
            enriched_chunks.append(chunk)
        return enriched_chunks
