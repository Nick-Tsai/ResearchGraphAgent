"""Abstract base class for model providers."""

from abc import ABC, abstractmethod


class ModelProvider(ABC):
    """Interface for LLM model providers."""

    @abstractmethod
    async def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        """Send a prompt and return the model's completion string."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name for logging/debugging."""
        ...
