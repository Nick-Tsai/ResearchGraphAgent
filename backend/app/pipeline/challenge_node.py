"""Challenge node: find counterarguments and weak assumptions for a node."""

import json
from uuid import UUID
from sqlmodel import Session, select
from app.models import GraphNode, Evidence
from app.providers.base import ModelProvider


CHALLENGE_PROMPT = """\
Challenge this graph node.

Find:
- assumptions that may be false
- missing evidence
- counterarguments
- alternate explanations
- search queries to verify or falsify the node

Return strict JSON:
{{
  "weak_assumptions": ["Assumption that may be false"],
  "missing_evidence": ["Missing evidence description"],
  "counterarguments": ["Counterargument"],
  "alternate_explanations": ["Alternate explanation"],
  "search_queries": ["Query to verify"],
  "summary": "Brief summary of the challenge analysis"
}}

Node:
{node_json}

Current supporting evidence:
{evidence_json}"""


async def challenge_node(
    node_id: UUID,
    project_id: UUID,
    provider: ModelProvider,
    session: Session,
) -> dict:
    """Challenge a graph node by finding counterarguments and weak assumptions."""
    node = session.get(GraphNode, node_id)
    if not node or str(node.project_id) != str(project_id):
        raise ValueError("Node not found")

    evidence_ids: list[UUID] = []
    for raw_id in node.evidence_ids:
        try:
            evidence_ids.append(UUID(str(raw_id)))
        except ValueError:
            continue

    query = select(Evidence).where(Evidence.project_id == project_id)
    if evidence_ids:
        query = query.where(Evidence.id.in_(evidence_ids))
    evidence_entries = session.exec(query).all()

    node_data = {
        "title": node.title,
        "summary": node.summary,
        "node_type": node.node_type,
        "confidence": node.confidence,
    }

    evidence_data = [
        {"id": str(e.id), "claim": e.claim, "confidence": e.confidence}
        for e in evidence_entries
    ]

    prompt = CHALLENGE_PROMPT.format(
        node_json=json.dumps(node_data, indent=2),
        evidence_json=json.dumps(evidence_data, indent=2),
    )

    raw = await provider.complete(prompt)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Challenge node returned invalid JSON")

    return {
        "node_id": str(node_id),
        "weak_assumptions": data.get("weak_assumptions", []),
        "missing_evidence": data.get("missing_evidence", []),
        "counterarguments": data.get("counterarguments", []),
        "alternate_explanations": data.get("alternate_explanations", []),
        "search_queries": data.get("search_queries", []),
        "summary": data.get("summary", ""),
    }
