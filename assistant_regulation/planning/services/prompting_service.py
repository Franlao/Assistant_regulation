from __future__ import annotations

"""prompting_service.py
Ce module fournit la classe `PromptingService` dont la responsabilité est de
centraliser la construction des différents prompts utilisés dans le projet.
En un seul endroit :
  • Maintenance simplifiée des templates
  • Cohérence entre les services
  • Possibilité d'internationalisation / versioning futur

La classe expose des méthodes spécialisées (par ex. `build_generation_prompt`)
et une méthode générique `build_prompt` si l'on souhaite choisir dynamiquement
en fonction d'un identifiant.

Les méthodes suivantes couvrent les besoins immédiats :
  - Prompt de génération de réponse finale (LLM)
  - Prompt de vérification de chunks (utilisé par le VerifAgent)
  - Prompt d'analyse de requête (QueryAnalysisAgent)

D'autres templates pourront être ajoutés sans modifier le reste du code
consommateur – il suffira d'appeler la nouvelle méthode ou de passer un
nouvel identifiant à `build_prompt`.
"""

from typing import Dict, Callable


class PromptingService:
    """Service de centralisation des templates de prompts."""

    # ------------------------------------------------------------------
    def __init__(self) -> None:
        # Table de routage optionnelle pour l'accès via `build_prompt`.
        self._builders: Dict[str, Callable[..., str]] = {
            "generation": self.build_generation_prompt,
            "verification": self.build_verification_prompt,
            "query_analysis": self.build_query_analysis_prompt,
        }

    # ==================================================================
    # Prompts *publics*
    # ==================================================================
    def build_generation_prompt(
        self,
        query: str,
        *,
        context: str = "",
        conversation_context: str = "",
    ) -> str:
        """Assemble le prompt envoyé au LLM pour générer la réponse finale.

        L'algorithme actuel reproduit la logique historique de
        `GenerationService.generate_answer` :
          1. Contexte conversationnel (si disponible)
          2. Contexte RAG (si disponible)
          3. Question utilisateur
        """
        prompt_parts: list[str] = []

        if conversation_context:
            prompt_parts.append(conversation_context)

        if context:
            prompt_parts.append("INFORMATIONS RÉGLEMENTAIRES:\n" + context + "\n")

        prompt_parts.append(f"QUESTION: {query}\n\nRéponse (en français):")
        return "\n\n".join(prompt_parts)

    # ------------------------------------------------------------------
    def build_verification_prompt(self, question: str, chunk: Dict) -> str:
        """Construit le prompt utilisé pour vérifier la pertinence d'un chunk.

        Reprise (quasi) identique de la logique de `VerifAgent._generate_verification_prompt`.
        L'objectif est d'éviter la duplication et de permettre au `VerifAgent`
        d'appeler ce service plutôt que de conserver sa propre implémentation.
        """
        chunk_type = chunk.get("type", "text")
        base_info = (
            f"Document: {chunk.get('document_name', 'Inconnu')}\n"
            f"Règlement: {chunk.get('regulation_code', 'INCONNU')}\n"
        )

        instruction = (
            """
CONTEXTE: Vous êtes un expert en réglementations automobiles chargé d'évaluer la pertinence d'un FRAGMENT de document pour répondre à une QUESTION.

OBJECTIF: Décider si le fragment contient des informations POTENTIELLEMENT utiles.

RÉPONDEZ STRICTEMENT par un objet JSON valide SANS commentaire ni Markdown.
Format attendu : {"useful": <true|false>, "confidence": <nombre entre 0 et 1>}

Définition des champs :
 • useful      : true si le fragment contient AU MOINS UNE information pertinente.
 • confidence  : score de confiance de votre évaluation.

EXEMPLES
────────────────────────────────
Question : Quelle est la largeur maximale autorisée d'un bus ?
Fragment : "La largeur maximale des véhicules M3 est fixée à 2,55 m..."
Réponse : {"useful": true, "confidence": 0.93}

Question : Quelle est la largeur maximale autorisée d'un bus ?
Fragment : "Les émissions sonores doivent être inférieures à 80 dB..."
Réponse : {"useful": false, "confidence": 0.88}
"""
        )

        if chunk_type == "image":
            return (
                f"{instruction}\n\n"
                "**[Évaluation d'Image]**\n"
                f"{base_info}"
                f"Contexte: {chunk.get('description', 'Aucune description')}\n"
                f"Page: {chunk.get('page_number', 'N/A')}\n\n"
                f"QUESTION: \"{question}\"\n\n"
                "Cette image contient-elle des informations potentiellement utiles pour cette question?"
            )

        if chunk_type == "table":
            return (
                f"{instruction}\n\n"
                "**[Évaluation de Tableau]**\n"
                f"{base_info}"
                f"Page: {chunk.get('page_number', 'N/A')}\n"
                "Contenu du tableau:\n"
                f"{str(chunk.get('content', '')).strip()[:2000]}\n\n"
                f"QUESTION: \"{question}\"\n\n"
                "Ce tableau contient-il des informations potentiellement utiles pour cette question?"
            )

        # Default: text chunk
        return (
            f"{instruction}\n\n"
            "**[Évaluation de Texte]**\n"
            f"{base_info}"
            f"Page: {chunk.get('page_number', 'N/A')}\n"
            "Contenu:\n"
            f"{chunk.get('content', '')[:2000]}\n\n"
            f"QUESTION: \"{question}\"\n\n"
            "Ce texte contient-il des informations potentiellement utiles pour cette question?"
        )

    # ------------------------------------------------------------------
    def build_query_analysis_prompt(self, query: str) -> str:
        """Prompt utilisé pour classer la requête (RAG ou non)."""
        # Pour éviter un énorme bloc de texte inline ici, on stocke seulement le
        # marqueur d'insertion et on délègue le template complet. Une version
        # simplifiée est suffisante pour l'instant ; le prompt original reste
        # dans `QueryAnalysisAgent`. Le service est prêt pour une migration
        # future.
        return (
            "Vous êtes un assistant chargé de classifier les questions d'un utilisateur.\n"  # noqa: E501
            "Déterminez si la question nécessite une recherche dans la base de RAG (réglementations automobiles).\n\n"
            "Question: \n" + query + "\n\n"
            "Répondez STRICTEMENT sous la forme JSON suivante :\n"
            "{\n  \"needs_rag\": <true/false>,\n  \"query_type\": <\"regulation|general|other\">\n}"
        )

    # ==================================================================
    # Méthode générique
    # ==================================================================
    def build_prompt(self, prompt_type: str, **kwargs) -> str:
        """Interface générique : construit un prompt selon son identifiant."""
        if prompt_type not in self._builders:
            raise ValueError(f"Prompt type inconnu : {prompt_type}")
        return self._builders[prompt_type](**kwargs) 