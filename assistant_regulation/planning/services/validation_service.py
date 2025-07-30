from typing import Dict

from assistant_regulation.processing.Modul_verif.verif_agent import VerifAgent


class ValidationService:
    """Service responsable de la validation/filtrage des chunks via un LLM."""

    def __init__(self, llm_provider: str = "ollama", model_name: str = "llama3.2") -> None:
        self.verif_agent = VerifAgent(llm_provider=llm_provider, model_name=model_name)

    # ------------------------------------------------------------------
    def validate_chunks(self, query: str, chunks: Dict) -> Dict:
        """Applique la validation pour chaque type de chunk si présent."""
        verified: Dict[str, list] = {}

        for key in ("text", "images", "tables"):
            if key in chunks:
                verified[key] = self.verif_agent.verify_chunks(query, chunks[key], top_k=8)
            else:
                verified[key] = []

        return verified 