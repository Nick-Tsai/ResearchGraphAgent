"""Search pipeline: run queries from IDPS plan, fetch and save sources."""

import re
import asyncio
from uuid import UUID
from sqlmodel import Session, select
from app.models import Project, Source, IDPSPlan
from app.providers.search_provider import SearchProvider

# ── Budget limits (per research-graph-agent.md §8) ────────
MAX_QUERIES_PER_RUN = 20
MAX_SOURCES_TOTAL = 30
MAX_SOURCE_CHARS = 20000


# Stop words for Chinese + English relevance filtering
_STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
    "of", "and", "or", "it", "its", "be", "by", "as", "with", "from", "that",
    "this", "these", "those", "has", "have", "had", "do", "does", "did",
    "的", "了", "是", "在", "和", "与", "及", "或", "对", "为", "被", "把", "从", "到",
    "不", "也", "就", "都", "而", "但", "所", "以", "之", "等", "个", "有", "人", "会",
    "可以", "没有", "自己", "什么", "这样", "如何", "因为", "所以",
}


def _tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from a text string, separating CJK characters individually."""
    text = text.lower()
    # Get all english/alphanumeric words
    words = re.findall(r'[a-zA-Z0-9_]+', text)
    tokens = {w for w in words if len(w) > 1 and w not in _STOP_WORDS}
    # Get all Chinese/CJK characters individually
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    for c in chinese_chars:
        if c not in _STOP_WORDS:
            tokens.add(c)
    return tokens


def _is_relevant(result_title: str, result_snippet: str, query: str, min_overlap: int = 2) -> bool:
    """Check if a search result has enough keyword overlap with the query."""
    query_tokens = _tokenize(query)
    result_text = f"{result_title} {result_snippet}".lower()
    result_tokens = _tokenize(result_text)

    if not query_tokens:
        return True

    overlap = query_tokens & result_tokens
    # Also check if any query token appears as substring in result
    substring_hits = sum(
        1 for qt in query_tokens
        if any(qt in rt for rt in result_tokens) or qt in result_text
    )
    return len(overlap) >= min_overlap or substring_hits >= min_overlap


async def run_search(project: Project, search_provider: SearchProvider, session: Session) -> list[Source]:
    """Run all initial search queries from the IDPS plan, fetch content, and save sources.
    Filters out low-relevance results and deduplicates across runs.
    """
    plan = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project.id)).first()
    if not plan:
        raise ValueError("No IDPS plan found. Run IDPS planning first.")

    existing_urls = {
        s for s in session.exec(
            select(Source.url).where(Source.project_id == project.id)
        ).all()
    }

    queries = list(plan.initial_search_queries[:MAX_QUERIES_PER_RUN])
    # Also use IDPS subquestions AND falsification tests as targeted search queries
    if plan.dimensions:
        # Collect priority queries (subquestions + falsification tests)
        priority_qs = []
        for d in plan.dimensions:
            priority_qs.extend(d.get("subquestions", []))
            priority_qs.extend(d.get("falsification_tests", []))
        # Priority queries go first, capped at ~70% of budget
        priority_budget = int(MAX_QUERIES_PER_RUN * 0.7)
        for q in priority_qs[:priority_budget]:
            if len(queries) < MAX_QUERIES_PER_RUN:
                queries.insert(0, q)  # prepend to run first

    async def search_query(q: str) -> list[dict]:
        results = await search_provider.search(q, limit=8)
        sources: list[dict] = []
        for r in results:
            if r.url in existing_urls:
                continue
            # Relevance filter
            if not _is_relevant(r.title, r.snippet, q):
                continue
            content = await search_provider.fetch_content(r.url)
            sources.append(
                {
                    "url": r.url,
                    "title": r.title,
                    "publisher": r.publisher,
                    "published_at": r.published_at,
                    "extracted_text": content[:MAX_SOURCE_CHARS],
                    "search_query": q,
                    "source_type": r.source_type,
                    "reliability_score": 0.7 if r.source_type == "primary" else 0.5,
                }
            )
        return sources

    tasks = [search_query(q) for q in queries]
    all_results = await asyncio.gather(*tasks)

    seen = set(existing_urls)
    unique_sources: list[Source] = []
    for batch in all_results:
        for source_data in batch:
            url = source_data["url"]
            if url in seen or len(unique_sources) >= MAX_SOURCES_TOTAL:
                continue
            seen.add(url)
            source = Source(project_id=project.id, **source_data)
            session.add(source)
            unique_sources.append(source)

    project.status = "running"
    session.add(project)
    session.commit()

    return unique_sources
