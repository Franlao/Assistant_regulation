from typing import Dict
import logging

from assistant_regulation.processing.Modul_verif.verif_agent import VerifAgent


class ValidationService:
    """Service responsable de la validation/filtrage des chunks via un LLM."""

    def __init__(self, llm_provider: str = "ollama", model_name: str = "llama3.2") -> None:
        self.verif_agent = VerifAgent(llm_provider=llm_provider, model_name=model_name)
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    def validate_chunks(self, query: str, chunks: Dict, use_parallel: bool = True,
                       skip_validation: bool = False) -> Dict:
        """Applique la validation pour chaque type de chunk si présent avec parallélisation optionnelle."""
        verified: Dict[str, list] = {}

        for key in ("text", "images", "tables"):
            if key in chunks and chunks[key]:
                chunk_count = len(chunks[key])

                # Validation conditionnelle : skip si peu de chunks ou scores élevés
                if skip_validation or self._should_skip_validation(chunks[key], query):
                    # Retourner directement les chunks sans validation
                    verified[key] = chunks[key][:10]  # Limiter à 10 chunks
                    print(f"[VALIDATION SKIP] Type: {key} - Count: {len(verified[key])} - Reason: conditional")
                    self.logger.info(f"VALIDATION SKIP - Type: {key} - Count: {len(verified[key])} - Reason: conditional")
                    continue

                # Déterminer si utiliser la parallélisation selon le nombre de chunks
                use_parallel_for_key = use_parallel and chunk_count > 2

                # Ajuster max_workers selon le type de chunk et leur nombre
                if key == "text":
                    max_workers = min(6, chunk_count)
                else:
                    max_workers = min(3, chunk_count)

                # Configuration plus permissive pour réduire les faux négatifs
                import time
                start_time = time.time()

                verified[key] = self.verif_agent.verify_chunks(
                    query,
                    chunks[key],
                    top_k=10,
                    confidence_threshold=0.5,
                    use_parallel=use_parallel_for_key,
                    max_workers=max_workers,
                    verbose=False
                )

                elapsed = time.time() - start_time
                mode = "PARALLEL" if use_parallel_for_key else "SEQUENTIAL"
                print(f"[VALIDATION {mode}] Type: {key} - Input: {chunk_count} - Output: {len(verified[key])} - Time: {elapsed:.3f}s - Workers: {max_workers}")
                self.logger.info(f"VALIDATION {mode} - Type: {key} - Input: {chunk_count} - Output: {len(verified[key])} - Time: {elapsed:.3f}s - Workers: {max_workers}")
            else:
                verified[key] = []

        return verified

    def _should_skip_validation(self, chunks: list, query: str) -> bool:
        """Détermine si la validation peut être évitée pour optimiser les performances."""
        if not chunks:
            return True

        # Skip si peu de chunks (< 3)
        if len(chunks) < 3:
            return True

        # Skip si tous les chunks ont un score élevé (> 0.8)
        high_score_count = sum(1 for chunk in chunks if chunk.get('score', 0) > 0.8)
        if high_score_count >= len(chunks) * 0.8:  # 80% des chunks ont un score élevé
            return True

        # Skip pour des requêtes spécifiques (réglementations spécifiques)
        specific_patterns = ['ECE R', 'UN R', 'R107', 'R46', 'R94', 'R95']
        if any(pattern in query.upper() for pattern in specific_patterns):
            return True

        return False 