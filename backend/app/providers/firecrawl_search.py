"""Firecrawl search provider with IP pool round-robin load balancing.

Pool configuration lives in backend/firecrawl_pool.json — not in .env.
Format:
{
  "instances": [
    {"url": "http://host:port", "api_key": "...", "weight": 1}
  ]
}
Set api_key to "" if instances are unauthenticated (no Authorization header sent).
"""

import json
import httpx
import itertools
import os
from app.providers.search_provider import SearchProvider, SearchResult


POOL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "firecrawl_pool.json")


def _load_pool() -> list[dict]:
    with open(POOL_PATH, "r") as f:
        data = json.load(f)
    instances = data.get("instances", [])
    if not instances:
        raise ValueError("firecrawl_pool.json has no instances configured")
    expanded = []
    for inst in instances:
        weight = max(1, int(inst.get("weight", 1)))
        for _ in range(weight):
            expanded.append(inst)
    return expanded


def _build_headers(api_key: str) -> dict[str, str]:
    """Build request headers. Omits Authorization when api_key is empty."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


class FirecrawlSearchProvider(SearchProvider):
    """Round-robin load-balanced Firecrawl search across an IP pool."""

    def __init__(self) -> None:
        self._pool = _load_pool()
        self._cycler = itertools.cycle(self._pool)

    @property
    def name(self) -> str:
        return "firecrawl"

    def _next_instance(self) -> dict:
        return next(self._cycler)

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        inst = self._next_instance()
        base = inst["url"].rstrip("/")
        headers = _build_headers(inst.get("api_key", ""))

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base}/v1/search",
                headers=headers,
                json={
                    "query": query,
                    "limit": limit,
                    "scrapeOptions": {"formats": ["markdown", "screenshot"]},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[SearchResult] = []
        for r in data.get("data", []):
            results.append(SearchResult(
                url=r.get("url", ""),
                title=r.get("title", ""),
                snippet=r.get("description", ""),
                publisher="firecrawl",
            ))
        return results

    async def fetch_content(self, url: str) -> str:
        inst = self._next_instance()
        base = inst["url"].rstrip("/")
        headers = _build_headers(inst.get("api_key", ""))

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base}/v1/scrape",
                headers=headers,
                json={"url": url, "formats": ["markdown", "screenshot"]},
            )
            resp.raise_for_status()
            data = resp.json()

        return data.get("data", {}).get("markdown", "")
