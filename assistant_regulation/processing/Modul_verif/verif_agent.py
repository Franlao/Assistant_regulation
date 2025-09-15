from typing import List, Dict, Union
import os
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Nouveau : service centralisé des prompts
from assistant_regulation.planning.services.prompting_service import PromptingService

# Service reranker facultatif
from assistant_regulation.planning.services.reranker_service import RerankerService

class VerifAgent:
    def __init__(
        self,
        model_name: str = "llama3",
        temperature: float = 0.0,
        llm_provider: str = "ollama",
        prompting_service: PromptingService | None = None,
        reranker_service: RerankerService | None = None,
    ):
        """
        Initialize verification agent with LLM configuration.
        
        Args:
            model_name (str): Name of the model to use
            temperature (float): Temperature parameter for LLM (0.0 = deterministic)
            llm_provider (str): Provider to use ("ollama" or "mistral")
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self.temperature = temperature
        self.llm_provider = llm_provider
        self.client = self._init_client()
        # Centralisation des prompts (possibilité d'injecter un mock en tests)
        self.prompting_service: PromptingService = prompting_service or PromptingService()
        self.reranker_service: RerankerService | None = reranker_service
        
    def _init_client(self):
        """Initialise le client LLM avec fallback"""
        if self.llm_provider == "mistral":
            try:
                from mistralai import Mistral
                api_key = os.getenv("MISTRAL_API_KEY")
                if api_key:
                    return {'type': 'mistral', 'client': Mistral(api_key=api_key)}
                else:
                    self.logger.error("MISTRAL_API_KEY environment variable not set")
            except ImportError:
                self.logger.error("Mistral package not installed, falling back to ollama")
        
        # Default to ollama if mistral isn't available or not specified
        try:
            import ollama
            return {'type': 'ollama', 'client': ollama}
        except Exception as e:
            raise RuntimeError(f"Impossible d'initialiser le client LLM: {e}")

    def _generate_verification_prompt(self, question: str, chunk: Dict) -> str:
        """Délègue la construction du prompt au `PromptingService`."""
        return self.prompting_service.build_verification_prompt(question, chunk)

    def verify_chunks(
        self,
        question: str,
        chunks: List[Dict],
        *,
        confidence_threshold: float = 0.7,
        top_k: int = 10,
        use_rerank: bool = True,
        verbose: bool = False,
        use_parallel: bool = True,
        max_workers: int = 4,
    ) -> List[Dict]:
        """Filtre les chunks via LLM avec parallélisation optionnelle.

        Étapes :
        1. (Optionnel) Rerank pour garder le top_k le plus pertinent.
        2. Question au LLM avec prompt JSON (séquentiel ou parallèle).
        3. Utilise le champ 'confidence' comparé au `confidence_threshold`.
        """

        # -------------------------------------------------------------
        # 0. Rerank (optionnel)
        # -------------------------------------------------------------
        if use_rerank and self.reranker_service and chunks:
            try:
                chunks = self.reranker_service.rerank_chunks(question, chunks, top_k=top_k)
            except Exception as e:
                self.logger.error(f"Rerank échoué: {e}")
        else:
            chunks = chunks[:top_k]

        if not chunks:
            return []

        # Décider entre parallèle et séquentiel selon le nombre de chunks
        if use_parallel and len(chunks) > 2:
            return self._verify_chunks_parallel(
                question, chunks, confidence_threshold, verbose, max_workers
            )
        else:
            return self._verify_chunks_sequential(
                question, chunks, confidence_threshold, verbose
            )

    def _verify_chunks_sequential(
        self,
        question: str,
        chunks: List[Dict],
        confidence_threshold: float,
        verbose: bool,
    ) -> List[Dict]:
        """Validation séquentielle (mode original)."""
        valid_chunks: List[Dict] = []

        for i, chunk in enumerate(chunks):
            try:
                result = self._verify_single_chunk(question, chunk, confidence_threshold)
                if result["is_relevant"]:
                    valid_chunks.append(result["chunk"])

            except Exception as e:
                self.logger.error(f"Erreur de vérification séquentielle chunk {i}: {str(e)}")
                continue

        return valid_chunks

    def _verify_chunks_parallel(
        self,
        question: str,
        chunks: List[Dict],
        confidence_threshold: float,
        verbose: bool,
        max_workers: int,
    ) -> List[Dict]:
        """Validation parallèle avec ThreadPoolExecutor."""
        valid_chunks: List[Dict] = []
        start_time = time.time()

        # Optimiser le nombre de workers selon le nombre de chunks
        optimal_workers = min(max_workers, len(chunks), 6)  # Max 6 pour éviter les timeouts

        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            # Soumettre toutes les tâches de validation
            future_to_chunk = {}
            for i, chunk in enumerate(chunks):
                future = executor.submit(
                    self._verify_single_chunk, question, chunk, confidence_threshold
                )
                future_to_chunk[future] = (i, chunk)

            # Collecter les résultats avec gestion d'erreurs robuste
            for future in as_completed(future_to_chunk, timeout=30):
                chunk_index, original_chunk = future_to_chunk[future]
                try:
                    result = future.result(timeout=5)  # Timeout per chunk
                    if result["is_relevant"]:
                        valid_chunks.append(result["chunk"])

                except Exception as e:
                    self.logger.warning(f"Validation parallèle échouée pour chunk {chunk_index}: {e}")
                    # En cas d'erreur, on peut décider d'inclure ou non le chunk
                    # Pour être conservatif, on l'inclut sans validation
                    valid_chunks.append({
                        **original_chunk,
                        'verification_response': f"Erreur: {str(e)}",
                        'verification_model': self.model_name,
                        'verification_confidence': 0.5,  # Score neutre
                    })

        elapsed = time.time() - start_time
        if verbose:
            self.logger.info(f"Validation parallèle: {len(chunks)} chunks en {elapsed:.2f}s "
                           f"({optimal_workers} workers) -> {len(valid_chunks)} valides")

        return valid_chunks

    def _verify_single_chunk(
        self, question: str, chunk: Dict, confidence_threshold: float
    ) -> Dict:
        """Valide un seul chunk et retourne le résultat structuré."""
        try:
            prompt = self._generate_verification_prompt(question, chunk)
            response = self._get_llm_response(prompt)
            useful, confidence = self._parse_llm_response(response)

            is_relevant = useful and (confidence is None or confidence >= confidence_threshold)

            if is_relevant:
                return {
                    "is_relevant": True,
                    "chunk": {
                        **chunk,
                        'verification_response': response,
                        'verification_model': self.model_name,
                        'verification_confidence': confidence,
                    }
                }
            else:
                return {
                    "is_relevant": False,
                    "chunk": {
                        **chunk,
                        'verification_response': response,
                        'verification_confidence': confidence,
                    }
                }

        except Exception as e:
            # En cas d'erreur, considérer le chunk comme valide avec score neutre
            return {
                "is_relevant": True,
                "chunk": {
                    **chunk,
                    'verification_response': f"Erreur validation: {str(e)}",
                    'verification_model': self.model_name,
                    'verification_confidence': 0.5,
                }
            }

    def _get_llm_response(self, prompt: str) -> str:
        """Obtient la réponse du LLM"""
        if self.client['type'] == 'mistral':
            response = self.client['client'].chat.complete(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=10
            )
            return response.choices[0].message.content.strip()
        else:
            response = self.client['client'].chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                options={'temperature': self.temperature, 'max_tokens': 20}
            )
            return response['message']['content'].strip()

    def _is_positive_response(self, response: str) -> bool:
        """Détecte une réponse affirmative avec une meilleure couverture"""
        positive_indicators = [
            "oui", "yes", "y", "valid", "correct", "pertinent", "utile", 
            "useful", "helpful", "relevant", "peut aider", "can help",
            "contient", "contains", "apporte", "provides", "positive"
        ]

        # Vérifie d'abord si la réponse contient explicitement "non" tout seul
        if response.lower().strip() == "non" or response.lower().strip() == "no":
            return False

        # Sinon, cherche des indicateurs positifs
        return any(keyword in response.lower() for keyword in positive_indicators)
    
    def test_verification(self, question: str, sample_chunk: Dict):
        """
        Fonction de diagnostic pour tester la vérification sur un seul chunk
        et afficher tous les détails du processus.
        """
        # Sorties de test verboses supprimées
        
        prompt = self._generate_verification_prompt(question, sample_chunk)
        
        
        response = self._get_llm_response(prompt)
        
        is_relevant = self._is_positive_response(response)
        return is_relevant

    # ------------------------------------------------------------------
    def _parse_llm_response(self, response: str) -> tuple[bool, float | None]:
        """Parse la réponse JSON {useful, confidence}. Fallback heuristique si besoin."""
        try:
            parsed = json.loads(response)
            useful = bool(parsed.get("useful", False))
            confidence = float(parsed.get("confidence")) if "confidence" in parsed else None
            return useful, confidence
        except Exception:
            # Fallback: heuristique ancienne
            useful = self._is_positive_response(response)
            return useful, None