from __future__ import annotations

from typing import List, Dict, Any

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

    # ------------------------------------------------------------------
    def _call_jina_api(self, query: str, docs: List[Any]) -> List[tuple[Any, float]]:
        """Envoie la requête POST à l'API Jina et renvoie la liste (doc, score)."""
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
        # Utiliser timeout depuis config
        response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
        if response.status_code >= 400:
            raise RuntimeError(f"Jina API error {response.status_code}: {response.text}")
        data = response.json()

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

        try:
            ranked_pairs = self.rerank(query, docs, top_k=top_k)
        except Exception as e:
            print(f"Jina rerank failed: {e}. Docs sent: {len(docs)}")
            # Fallback: retourner les chunks dans l'ordre original avec scores par défaut
            print("Fallback: retour des chunks sans reranking")
            for idx, chunk in enumerate(index_to_chunk):
                chunk["rerank_score"] = 1.0 - (idx * 0.1)  # Score décroissant simple
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
