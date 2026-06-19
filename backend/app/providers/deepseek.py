"""DeepSeek model provider with shared httpx client."""

import httpx
from app.providers.base import ModelProvider
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class DeepSeekProvider(ModelProvider):
    """Calls the DeepSeek chat-completion API. Uses a single shared httpx client."""

    def __init__(self) -> None:
        self._api_key = DEEPSEEK_API_KEY
        self._base_url = DEEPSEEK_BASE_URL.rstrip("/")
        self._model = DEEPSEEK_MODEL
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "deepseek"

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(300.0, connect=30.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    async def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        if not self._api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set")

        url = f"{self._base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }

        response = await self._get_client().post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason", "unknown")

        if not content or not content.strip():
            raise ValueError(
                f"DeepSeek returned empty content. "
                f"finish_reason={finish_reason}, model={self._model}, "
                f"max_tokens={max_tokens}"
            )

        return self._strip_code_fences(content)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
