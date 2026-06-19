"""Provider factory: selects the model provider based on configuration."""

from functools import lru_cache

from app.providers.base import ModelProvider
from app.providers.mock import MockProvider
from app.providers.deepseek import DeepSeekProvider
from app.config import MODEL_PROVIDER, DEEPSEEK_API_KEY


@lru_cache(maxsize=1)
def get_provider() -> ModelProvider:
    """Return the configured model provider instance."""
    if MODEL_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
        return DeepSeekProvider()
    return MockProvider()
