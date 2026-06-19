"""Premium review: compress the graph and send to a premium model for critique."""

import json
from uuid import UUID
from sqlmodel import Session, select
from app.models import Project, GraphNode, GraphEdge, Evidence, IDPSPlan
from app.providers.base import ModelProvider


PREMIUM_REVIEW_PROMPT = """\
You are the premium review model for a research graph agent.

Review the compressed research graph.

Focus on:
- flawed assumptions
- weak evidence
- missing dimensions
- contradictions that were not resolved
- better structure for the topic graph
- what the user should investigate next

Do not rewrite everything. Produce a concise critique and specific graph edits.

Return strict JSON:
{{
  "overall_assessment": "Overall assessment",
  "critical_issues": ["Critical issue"],
  "missing_dimensions": ["Missing dimension"],
  "contradictions_to_resolve": ["Contradiction"],
  "recommended_node_edits": [
    {{"node_title": "Title", "edit": "Suggested edit"}}
  ],
  "next_research_actions": ["Action to take next"],
  "confidence_improvement": 0.0
}}

Compressed graph:
{compressed_graph}"""


async def premium_review(
    project_id: UUID,
    provider: ModelProvider,
    session: Session,
) -> dict:
    """Send a compressed graph to a premium model for critique."""
    project = session.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    plan = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project_id)).first()
    nodes = session.exec(
        select(GraphNode).where(GraphNode.project_id == project_id).limit(30)
    ).all()
    edges = session.exec(
        select(GraphEdge).where(GraphEdge.project_id == project_id).limit(50)
    ).all()

    compressed = {
        "topic": project.topic,
        "problem_restatement": plan.problem_restatement if plan else "",
        "nodes": [
            {
                "title": n.title,
                "summary": n.summary[:200],
                "node_type": n.node_type,
                "confidence": n.confidence,
            }
            for n in nodes
        ],
        "edges": [
            {"source": e.source_node_id, "target": e.target_node_id, "relation": e.relation}
            for e in edges
        ],
        "risk_flags": plan.risk_flags if plan else [],
    }

    prompt = PREMIUM_REVIEW_PROMPT.format(
        compressed_graph=json.dumps(compressed, indent=2)
    )

    raw = await provider.complete(prompt)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Premium review returned invalid JSON")

    return {
        "overall_assessment": data.get("overall_assessment", ""),
        "critical_issues": data.get("critical_issues", []),
        "missing_dimensions": data.get("missing_dimensions", []),
        "contradictions_to_resolve": data.get("contradictions_to_resolve", []),
        "recommended_node_edits": data.get("recommended_node_edits", []),
        "next_research_actions": data.get("next_research_actions", []),
        "confidence_improvement": data.get("confidence_improvement", 0.0),
    }
