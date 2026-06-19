"""Expand node: break a graph node into subquestions and new search results."""

import json
from uuid import UUID
from sqlmodel import Session, select
from app.models import Project, GraphNode, IDPSPlan
from app.providers.base import ModelProvider
from app.providers.search_provider import SearchProvider


EXPAND_PROMPT = """\
Expand this graph node into 3-6 subquestions. Identify missing evidence, likely counterarguments, and search queries.

Return strict JSON:
{{
  "subquestions": ["Question 1", "Question 2"],
  "counterarguments": ["Counterargument 1"],
  "missing_evidence": ["Missing evidence description"],
  "search_queries": ["Query 1", "Query 2"],
  "summary": "Brief summary of expanded analysis"
}}

Node title:
{title}

Node summary:
{summary}

Node type:
{node_type}

Research topic:
{topic}"""


async def expand_node(
    node_id: UUID,
    project_id: UUID,
    provider: ModelProvider,
    search_provider: SearchProvider,
    session: Session,
) -> dict:
    """Expand a graph node into subquestions, and run a search for those queries."""
    node = session.get(GraphNode, node_id)
    if not node or str(node.project_id) != str(project_id):
        raise ValueError("Node not found")

    project = session.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    plan = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project_id)).first()
    topic = project.topic

    prompt = EXPAND_PROMPT.format(
        title=node.title,
        summary=node.summary,
        node_type=node.node_type,
        topic=topic,
    )

    raw = await provider.complete(prompt)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Expand node returned invalid JSON")

    # Optionally run searches for the generated queries
    search_results = []
    for q in data.get("search_queries", [])[:3]:
        results = await search_provider.search(q, limit=2)
        search_results.extend([{"title": r.title, "url": r.url, "snippet": r.snippet} for r in results])

    return {
        "node_id": str(node_id),
        "subquestions": data.get("subquestions", []),
        "counterarguments": data.get("counterarguments", []),
        "missing_evidence": data.get("missing_evidence", []),
        "search_queries": data.get("search_queries", []),
        "summary": data.get("summary", ""),
        "search_results": search_results,
    }
