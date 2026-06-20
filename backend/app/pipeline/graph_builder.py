"""Graph builder: dimension-first DSL generation + memory-first compiler."""

import asyncio
import re
from typing import Any
from sqlmodel import Session, select

from app.models import Project, IDPSPlan, Evidence, GraphNode, GraphEdge
from app.providers.base import ModelProvider
from app.pipeline.semantic_classifier import TfidfClassifier


DIM_NODE_PROMPT = """\
You are writing structured research notes for the dimension "{dim_name}".

Dimension description:
{dim_desc}

Research topic:
{topic}

Target audience: {audience}

Key questions to address (from IDPS analysis):
{subquestions_text}

Falsification tests to verify:
{falsification_text}

Available evidence claims (use only the relevant evidence IDs):
{evidence_lines}

Return a WEAKLY-STRUCTURED DSL using this exact shape:

# Dimension: {dim_name}
[NODE]
Type: claim|question|gap|contradiction
Title: short node title
Summary: 1-3 sentence summary
Evidence: ev-id-1, ev-id-2

[NODE]
Type: claim|question|gap|contradiction
Title: short node title
Summary: 1-3 sentence summary
Evidence: ev-id-3

Rules:
- Produce 2-6 nodes specific to this dimension.
- If evidence is weak or missing, include at least one gap or contradiction node.
- Evidence line may be empty for a gap node.
- Return ONLY the DSL, no JSON, no markdown fences, no prose outside the DSL.
"""


GLOBAL_RELATIONS_PROMPT = """\
You are connecting a research graph across dimensions.

Research topic:
{topic}

Target audience: {audience}

Nodes:
{nodes_lines}

Return a WEAKLY-STRUCTURED DSL using this exact shape:

[EDGE]
From: exact source node title
To: exact target node title
Relation: supports|contradicts|expands|depends_on|similar_to
Confidence: 0.0-1.0
Reason: one short reason

[EDGE]
From: exact source node title
To: exact target node title
Relation: supports|contradicts|expands|depends_on|similar_to
Confidence: 0.0-1.0
Reason: one short reason

Rules:
- Prefer cross-dimension links when meaningful.
- Include contradiction edges when evidence or reasoning conflicts.
- Return ONLY the DSL, no JSON, no markdown fences, no prose outside the DSL.
"""


def _clean_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _parse_key_value_blocks(raw: str, marker: str) -> list[dict[str, str]]:
    text = _clean_text(raw)
    pieces = re.split(rf"(?=^{re.escape(marker)}\s*$)", text, flags=re.MULTILINE)
    blocks: list[dict[str, str]] = []

    for piece in pieces:
        piece = piece.strip()
        if not piece.startswith(marker):
            continue
        data: dict[str, str] = {}
        current_key: str | None = None
        current_lines: list[str] = []
        for line in piece.splitlines()[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if ":" in stripped:
                if current_key is not None:
                    data[current_key] = "\n".join(current_lines).strip()
                key, value = stripped.split(":", 1)
                current_key = key.strip().lower()
                current_lines = [value.strip()]
            elif current_key is not None:
                current_lines.append(stripped)
        if current_key is not None:
            data[current_key] = "\n".join(current_lines).strip()
        if data:
            blocks.append(data)
    return blocks


def _parse_node_dsl(raw: str) -> list[dict[str, Any]]:
    blocks = _parse_key_value_blocks(raw, "[NODE]")
    nodes: list[dict[str, Any]] = []
    for block in blocks:
        title = block.get("title", "").strip()
        summary = block.get("summary", "").strip()
        node_type = block.get("type", "claim").strip().lower()
        evidence_raw = block.get("evidence", "").strip()
        evidence_ids = [item.strip() for item in evidence_raw.split(",") if item.strip()]
        if title:
            nodes.append(
                {
                    "title": title,
                    "summary": summary,
                    "node_type": node_type or "claim",
                    "evidence_ids": evidence_ids,
                }
            )
    return nodes


def _parse_edge_dsl(raw: str) -> list[dict[str, Any]]:
    blocks = _parse_key_value_blocks(raw, "[EDGE]")
    edges: list[dict[str, Any]] = []
    for block in blocks:
        source_title = block.get("from", "").strip()
        target_title = block.get("to", "").strip()
        relation = block.get("relation", "supports").strip().lower()
        confidence_raw = block.get("confidence", "0.5").strip()
        try:
            confidence = float(confidence_raw)
        except ValueError:
            confidence = 0.5
        if source_title and target_title:
            edges.append(
                {
                    "source_title": source_title,
                    "target_title": target_title,
                    "relation": relation or "supports",
                    "confidence": confidence,
                    "reason": block.get("reason", "").strip(),
                }
            )
    return edges


def _fallback_dimension_nodes(dim_name: str, dim_desc: str) -> str:
    return f"""# Dimension: {dim_name}
[NODE]
Type: gap
Title: Gap: {dim_name}
Summary: No reliable structured notes were generated for this dimension yet.
Evidence:
"""


async def build_graph(
    project: Project,
    provider: ModelProvider,
    session: Session,
) -> tuple[list[GraphNode], list[GraphEdge], str]:
    plan = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project.id)).first()
    evidence_entries = session.exec(
        select(Evidence).where(Evidence.project_id == project.id).limit(60)
    ).all()

    dimensions = plan.dimensions if plan else []
    if not dimensions:
        raise ValueError("No dimensions in IDPS plan")
    if not evidence_entries:
        raise ValueError("No evidence available for graph building")

    evidence_lines = "\n".join(
        f"- {str(e.id)} | cf={e.confidence:.2f} | {e.claim[:220]}"
        for e in evidence_entries
    )

    async def build_dimension_block(dim: dict, dim_idx: int) -> tuple[dict, str]:
        dim_name = dim["name"]
        dim_desc = dim.get("description", "")
        subquestions_text = "\n".join(f"- {q}" for q in dim.get("subquestions", []))
        falsification_text = "\n".join(f"- {q}" for q in dim.get("falsification_tests", []))
        audience = project.audience_level or "high"
        prompt = DIM_NODE_PROMPT.format(
            dim_name=dim_name,
            dim_desc=dim_desc,
            topic=project.topic,
            audience=audience,
            subquestions_text=subquestions_text,
            falsification_text=falsification_text,
            evidence_lines=evidence_lines,
        )
        raw = await provider.complete(prompt, max_tokens=8192)
        raw = _clean_text(raw)
        if "[NODE]" not in raw:
            raw = _fallback_dimension_nodes(dim_name, dim_desc)
        return dim, raw

    semaphore = asyncio.Semaphore(3)

    async def limited(dim: dict, idx: int):
        async with semaphore:
            return await build_dimension_block(dim, idx)

    dimension_results = await asyncio.gather(*(limited(dim, idx) for idx, dim in enumerate(dimensions)), return_exceptions=True)

    all_nodes: list[GraphNode] = []
    compiled_edges: list[GraphEdge] = []
    compiler_sections: list[str] = []
    title_to_id: dict[str, str] = {}

    for dim_idx, result in enumerate(dimension_results):
        dim = dimensions[dim_idx]
        dim_name = dim["name"]
        dim_desc = dim.get("description", "")
        if isinstance(result, Exception):
            raw_block = _fallback_dimension_nodes(dim_name, dim_desc)
        else:
            _, raw_block = result
        compiler_sections.append(raw_block)

        dim_node = GraphNode(
            project_id=project.id,
            title=dim_name,
            summary=dim_desc,
            node_type="dimension",
            confidence=1.0,
            evidence_ids=[],
            source_ids=[],
            x=float(dim_idx % 4) * 250 + 50,
            y=float(dim_idx // 4) * 220 + 50,
        )
        session.add(dim_node)
        session.flush()
        all_nodes.append(dim_node)
        title_to_id[dim_node.title] = str(dim_node.id)

        parsed_nodes = _parse_node_dsl(raw_block)
        if not parsed_nodes:
            parsed_nodes = _parse_node_dsl(_fallback_dimension_nodes(dim_name, dim_desc))

        for j, parsed in enumerate(parsed_nodes):
            child = GraphNode(
                project_id=project.id,
                title=parsed["title"],
                summary=parsed["summary"],
                node_type=parsed["node_type"],
                confidence=0.75 if parsed["node_type"] == "claim" else 0.6,
                evidence_ids=[str(eid) for eid in parsed["evidence_ids"]],
                source_ids=[],
                parent_node_id=str(dim_node.id),
                x=float(dim_idx % 4) * 250 + 50,
                y=float(dim_idx // 4) * 220 + 110 + j * 78,
            )
            session.add(child)
            session.flush()
            all_nodes.append(child)
            title_to_id[child.title] = str(child.id)
            edge = GraphEdge(
                project_id=project.id,
                source_node_id=str(dim_node.id),
                target_node_id=str(child.id),
                relation="expands",
                confidence=0.9,
            )
            session.add(edge)
            compiled_edges.append(edge)

    nodes_lines = "\n".join(
        f"- {node.title} | type={node.node_type} | summary={node.summary[:160]}"
        for node in all_nodes
        if node.node_type != "dimension"
    )
    audience = project.audience_level or "high"
    review_prompt = GLOBAL_RELATIONS_PROMPT.format(
        topic=project.topic,
        audience=audience,
        nodes_lines=nodes_lines,
    )
    relations_raw = _clean_text(await provider.complete(review_prompt, max_tokens=16384))
    compiler_sections.append("# Relations\n" + relations_raw)

    edges: list[GraphEdge] = list(compiled_edges)
    for parsed in _parse_edge_dsl(relations_raw):
        src_id = title_to_id.get(parsed["source_title"])
        tgt_id = title_to_id.get(parsed["target_title"])
        if src_id and tgt_id:
            edge = GraphEdge(
                project_id=project.id,
                source_node_id=src_id,
                target_node_id=tgt_id,
                relation=parsed["relation"],
                confidence=parsed["confidence"],
            )
            session.add(edge)
            edges.append(edge)

    session.commit()
    graph_memory = "\n\n".join(compiler_sections)
    return all_nodes, edges, graph_memory
