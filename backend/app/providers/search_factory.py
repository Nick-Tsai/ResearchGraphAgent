"""Search provider factory with layered fallback: Firecrawl -> Tavily -> Mock."""

from app.providers.search_provider import SearchProvider, SearchResult, MockSearchProvider
from app.providers.tavily_search import TavilySearchProvider
from app.providers.firecrawl_search import FirecrawlSearchProvider
from app.config import SEARCH_PROVIDER, TAVILY_API_KEY


class FallbackSearchProvider(SearchProvider):
    """Try providers in order; first non-empty result wins."""

    def __init__(self, providers: list[SearchProvider]):
        if not providers:
            raise ValueError("At least one provider required")
        self._providers = providers

    @property
    def name(self) -> str:
        return "+".join(p.name for p in self._providers)

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        for provider in self._providers:
            try:
                results = await provider.search(query, limit)
                if results:
                    return results
            except Exception:
                continue
        return []

    async def fetch_content(self, url: str) -> str:
        for provider in self._providers:
            try:
                content = await provider.fetch_content(url)
                if content:
                    return content
            except Exception:
                continue
        return ""


def get_search_provider() -> SearchProvider:
    """Return the configured search provider chain. Mock is always the final fallback."""
    chain: list[SearchProvider] = []

    if SEARCH_PROVIDER == "firecrawl":
        try:
            chain.append(FirecrawlSearchProvider())
        except (ValueError, FileNotFoundError):
            pass

    if SEARCH_PROVIDER in ("firecrawl", "tavily") and TAVILY_API_KEY:
        chain.append(TavilySearchProvider())

    # Mock is ALWAYS the final safety net
    chain.append(MockSearchProvider())

    if len(chain) == 1:
        return chain[0]
    return FallbackSearchProvider(chain)
