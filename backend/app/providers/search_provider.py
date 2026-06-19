"""Search provider interface and mock implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    publisher: str = ""
    published_at: str = ""
    source_type: str = "secondary"


class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    async def fetch_content(self, url: str) -> str:
        """Fetch and extract text content from a URL. Optional override."""
        return ""


MOCK_SEARCH_RESULTS = {
    "research graph AI agent source backed summaries": [
        SearchResult("https://arxiv.org/abs/2305.15334", "Graph-based AI Research Agents: A Survey", "Comprehensive survey of research agents using graph structures for source-backed summarization and knowledge discovery.", "arXiv", "2023-05-24", "primary"),
        SearchResult("https://blog.langchain.dev/research-agent-graph/", "Building a Research Agent with LangGraph", "Tutorial on constructing a research agent that creates knowledge graphs with source citations from search results.", "LangChain Blog", "2024-01-15", "secondary"),
    ],
    "topic graph exploration tool AI research workflow": [
        SearchResult("https://www.semanticscholar.org/paper/exploration-graphs", "Interactive Knowledge Graphs for Research Exploration", "Study of interactive graph exploration tools for academic research workflows, showing 40% improved discovery.", "Semantic Scholar", "2022-11-08", "primary"),
        SearchResult("https://obsidian.md/graph-view", "Obsidian Graph View for Research Notes", "How bidirectional linking and graph visualization help researchers connect ideas and spot gaps.", "Obsidian Blog", "2023-06-20", "secondary"),
    ],
    "LLM research agent citation graph architecture": [
        SearchResult("https://arxiv.org/abs/2310.12345", "Citation Graph Agents: LLM-Powered Literature Review", "Architecture for LLM agents that traverse citation graphs to produce structured literature reviews with provenance.", "arXiv", "2023-10-18", "primary"),
        SearchResult("https://github.com/stanford-oval/storm", "STORM: Synthesis of Topic Outlines through Retrieval and Multi-perspective Question Asking", "Stanford OVAL's system for automated knowledge curation using LLMs and retrieval.", "GitHub", "2024-03-01", "primary"),
    ],
    "interactive knowledge graph research assistant": [
        SearchResult("https://www.connectedpapers.com/about", "Connected Papers: Visual Tool for Academic Research", "How interactive graph-based exploration helps researchers find related papers and understand fields.", "Connected Papers", "2023-01-01", "secondary"),
    ],
    "default": [
        SearchResult("https://example.com/research-1", "Research Paper on Topic Analysis", "A detailed study examining the given research topic from multiple angles.", "Journal of Research", "2024-01-01", "secondary"),
        SearchResult("https://example.com/article-2", "Practical Guide to Research Methods", "Comprehensive guide covering methodologies relevant to the research question.", "Research Methods Press", "2023-06-15", "secondary"),
        SearchResult("https://example.com/whitepaper-3", "Industry Whitepaper: Current State and Future", "Industry analysis providing data-driven insights.", "Industry Corp", "2024-03-01", "secondary"),
    ],
}

MOCK_CONTENT = {
    "https://arxiv.org/abs/2305.15334": "Graph-based research agents represent a paradigm shift in automated knowledge work. By structuring research findings as graph nodes with explicit source edges, these systems achieve higher accuracy and traceability than linear summary approaches. Key findings: 1) Graph-structured knowledge bases reduce hallucination by 47% compared to pure LLM output. 2) Source-backed nodes increase user trust by 3.2x in controlled studies. 3) Interactive graph exploration enables serendipitous discovery that linear search misses. Limitations include computational cost of graph maintenance and difficulty with real-time updates.",
    "https://blog.langchain.dev/research-agent-graph/": "LangChain's LangGraph provides a framework for building research agents that maintain state as a graph. The architecture uses nodes for research tasks (search, summarize, critique) and edges for control flow. The key insight is treating the research process as a directed graph where each node produces structured output with citations. Implementation challenges include managing token budgets across graph traversal and handling contradictory evidence.",
    "https://arxiv.org/abs/2310.12345": "This paper presents a citation graph agent architecture that leverages LLMs for literature review. The system performs iterative expansion of citation graphs, using LLM judgment to prioritize which papers to explore. Results show 28% improvement in recall over keyword-based search. The architecture treats each paper as a graph node with citation edges, using the LLM to extract claims and identify conflicts.",
    "https://github.com/stanford-oval/storm": "STORM is a system for automated knowledge curation. It uses: 1) Perspective-guided question asking to discover diverse viewpoints, 2) Multi-turn simulated conversations with retrieved sources, 3) Structured outline generation with citation grounding. The system produces Wikipedia-style articles with inline citations. Evaluations show STORM articles are preferred by 70% of reviewers over baseline LLM outputs.",
}


class MockSearchProvider(SearchProvider):
    @property
    def name(self) -> str:
        return "mock_search"

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        for key, results in MOCK_SEARCH_RESULTS.items():
            if key in query.lower() or any(w in query.lower() for w in key.split()[:3]):
                return results[:limit]
        return MOCK_SEARCH_RESULTS["default"][:limit]

    async def fetch_content(self, url: str) -> str:
        return MOCK_CONTENT.get(url, "No mock content available for this URL.")
