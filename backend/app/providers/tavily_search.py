"""Tavily search provider — real web search via Tavily API."""

import httpx
from dataclasses import dataclass
from app.providers.search_provider import SearchProvider, SearchResult
from app.config import TAVILY_API_KEY, TAVILY_BASE_URL


class TavilySearchProvider(SearchProvider):
    """Calls the Tavily Search API."""

    def __init__(self) -> None:
        self._api_key = TAVILY_API_KEY
        self._base_url = TAVILY_BASE_URL.rstrip("/")

    @property
    def name(self) -> str:
        return "tavily"

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if not self._api_key:
            raise ValueError("TAVILY_API_KEY is not set")

        url = f"{self._base_url}/search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": limit,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for r in data.get("results", []):
            results.append(SearchResult(
                url=r.get("url", ""),
                title=r.get("title", ""),
                snippet=r.get("content", ""),
                publisher="tavily",
            ))
        return results

    async def fetch_content(self, url: str) -> str:
        """Tavily can extract content directly."""
        if not self._api_key:
            return ""

        extract_url = f"{self._base_url}/extract"
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": self._api_key,
            "urls": [url],
            "include_images": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(extract_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if results:
            return results[0].get("raw_content", "")
        return ""
