from typing import List, Dict, Union
import os
import logging
import json

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
    ) -> List[Dict]:
        """Filtre les chunks via LLM.

        Étapes :
        1. (Optionnel) Rerank pour garder le top_k le plus pertinent.
        2. Question au LLM avec prompt JSON.
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

        valid_chunks: List[Dict] = []
        rejected_chunks: List[Dict] = []

        for i, chunk in enumerate(chunks):
            try:
                if verbose:
                    # Logs de debug supprimés
                    pass

                prompt = self._generate_verification_prompt(question, chunk)

                if verbose:
                    # Logs de debug supprimés
                    pass

                response = self._get_llm_response(prompt)

                if verbose:
                    # Logs de debug supprimés
                    pass

                useful, confidence = self._parse_llm_response(response)

                is_relevant = useful and (confidence is None or confidence >= confidence_threshold)

                if verbose:
                    # Logs de debug supprimés
                    pass

                if is_relevant:
                    valid_chunks.append({
                        **chunk,
                        'verification_response': response,
                        'verification_model': self.model_name,
                        'verification_confidence': confidence,
                    })
                else:
                    rejected_chunks.append({
                        **chunk,
                        'verification_response': response,
                        'verification_confidence': confidence,
                    })

            except Exception as e:
                self.logger.error(f"Erreur de vérification: {str(e)}")
                if verbose:
                    # Log détaillé supprimé en mode silencieux
                    pass
                continue
            
        if verbose:
            # Logs de debug supprimés
            pass

        return valid_chunks

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