"""Services layer for the modular orchestrator.
Each service encapsulates a single business responsibility and can be easily
mocked or replaced during unit testing.
"""

from .retrieval_service import RetrievalService  # noqa: F401
from .generation_service import GenerationService  # noqa: F401
from .memory_service import MemoryService  # noqa: F401
from .context_builder_service import ContextBuilderService  # noqa: F401
from .reranker_service import RerankerService  # noqa: F401
from .prompting_service import PromptingService  # noqa: F401 


# Lazy import to avoid circular dependency issues (e.g., VerifAgent ↔ ValidationService)
def __getattr__(name):  # type: ignore
    """Dynamically load heavy or circular-dependent services on demand."""
    if name == "ValidationService":
        from .validation_service import ValidationService  # local import to break circularity
        return ValidationService
    raise AttributeError(f"module {__name__} has no attribute {name}") 