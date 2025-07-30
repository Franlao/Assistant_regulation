from typing import Dict

from dotenv import load_dotenv

from assistant_regulation.planning.services.prompting_service import PromptingService

load_dotenv()


class GenerationService:
    """Wraps LLM providers to generate answers.

    Cette implémentation supporte Mistral ou Ollama via une API simple.
    """

    def __init__(
        self,
        llm_provider: str = "ollama",
        model_name: str = "llama3.2",
        prompting_service: PromptingService | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.client = self._init_client()
        self.prompting_service: PromptingService = prompting_service or PromptingService()

    # ------------------------------------------------------------------
    def _init_client(self):
        if self.llm_provider == "mistral":
            try:
                from mistralai import Mistral
                import os

                api_key = os.getenv("MISTRAL_API_KEY")
                if not api_key:
                    raise EnvironmentError("MISTRAL_API_KEY is not set")
                return {"type": "mistral", "client": Mistral(api_key=api_key)}
            except ImportError as exc:
                raise ImportError("Please install `mistralai` to use the Mistral provider") from exc
        else:
            try:
                import ollama

                return {"type": "ollama", "client": ollama}
            except ImportError as exc:
                raise ImportError("Please install `ollama` to use the Ollama provider") from exc

    # ------------------------------------------------------------------
    def generate_answer(
        self,
        query: str,
        context: str = "",
        conversation_context: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Genère la réponse finale à partir du contexte fourni."""
        full_prompt: str = self.prompting_service.build_generation_prompt(
            query,
            context=context,
            conversation_context=conversation_context,
        )

        if self.client["type"] == "mistral":
            response = self.client["client"].chat.complete(
                model=self.model_name,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        else:  # ollama
            response = self.client["client"].chat(
                model=self.model_name,
                messages=[{"role": "user", "content": full_prompt}],
                options={"temperature": temperature},
            )
            return response["message"]["content"]

    # ------------------------------------------------------------------
    def generate_answer_stream(
        self,
        query: str,
        context: str = "",
        conversation_context: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ):
        """Genère la réponse finale en streaming à partir du contexte fourni."""
        full_prompt: str = self.prompting_service.build_generation_prompt(
            query,
            context=context,
            conversation_context=conversation_context,
        )

        if self.client["type"] == "mistral":
            response = self.client["client"].chat.stream(
                model=self.model_name,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            for chunk in response:
                content = chunk.data.choices[0].delta.content
                if content:
                    yield {"type": "text", "content": content}
        else:  # ollama
            response = self.client["client"].chat(
                model=self.model_name,
                messages=[{"role": "user", "content": full_prompt}],
                options={"temperature": temperature},
                stream=True,
            )
            for chunk in response:
                content = chunk["message"]["content"]
                if content:
                    yield {"type": "text", "content": content}

    # Expose client for low-level use (e.g., MemoryService)
    @property
    def raw_client(self):
        return self.client 