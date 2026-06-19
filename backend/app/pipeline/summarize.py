"""Summarizer pipeline: extract claims from source text using the model provider."""

import json
import asyncio
from sqlmodel import Session, select
from app.models import Project, Source, Evidence, IDPSPlan
from app.providers.base import ModelProvider


SUMMARIZE_PROMPT = """\
Summarize this source for a research graph.

Extract:
- main claims
- supporting evidence
- numbers, dates, and named entities
- limitations or uncertainty
- possible bias
- relevance to the research topic

Return strict JSON:
{{
  "claims": [
    {{
      "claim": "The main claim statement",
      "support_text": "Direct supporting text from source",
      "confidence": 0.0,
      "tags": ["keyword1", "keyword2"]
    }}
  ],
  "limitations": ["limitation 1"],
  "relevance_score": 0.0
}}

Research topic:
{topic}

Target audience: {audience}
(Craft explanations that a {audience} student would understand. Use metaphors and examples for elementary, intuitive analogies for middle school, clear definitions for high school, keep it academic for college.)

Relevant dimensions and their key questions (focus on answering these):
{dim_context}

Source title:
{title}

Source text:
{text}"""

MAX_CONCURRENT = 5  # limit parallel DeepSeek calls
MAX_SOURCE_CHARS = 20000


async def summarize_sources(
    project: Project,
    provider: ModelProvider,
    session: Session,
) -> list[Evidence]:
    """Summarize all sources for a project and extract evidence.
    Limits concurrency to MAX_CONCURRENT to avoid overwhelming the model API.
    Individual source failures are logged but do not block the pipeline.
    """
    sources = session.exec(
        select(Source).where(Source.project_id == project.id)
    ).all()

    if not sources:
        raise ValueError("No sources found. Run search first.")

    # Skip sources that already have evidence
    existing_source_ids = {
        e for e in session.exec(
            select(Evidence.source_id).where(Evidence.project_id == project.id)
        ).all()
    }
    sources = [s for s in sources if s.id not in existing_source_ids]

    if not sources:
        return []

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    all_evidence: list[Evidence] = []

    plan = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project.id)).first()
    async def process_source(source: Source) -> list[Evidence]:
        async with semaphore:
            try:
                dim_qs = []
                if plan and plan.dimensions:
                    for d in plan.dimensions:
                        for q in d.get("subquestions", [])[:2]:
                            dim_qs.append(f"  [Q] [{d.get('name', '')}] {q}")
                        for q in d.get("falsification_tests", [])[:1]:
                            dim_qs.append(f"  [VERIFY] [{d.get('name', '')}] {q}")
                dim_context = "\n".join(dim_qs) if dim_qs else "(no specific questions)"

                audience = project.audience_level or "high"
                prompt = SUMMARIZE_PROMPT.format(
                    audience=audience,
                    topic=project.topic,
                    dim_context=dim_context,
                    title=source.title,
                    text=source.extracted_text[:MAX_SOURCE_CHARS],
                )
                raw = await provider.complete(prompt)
                data = json.loads(raw)
            except Exception as exc:
                raise ValueError(f"Failed to summarize source {source.id}: {exc}") from exc

        claims_data = data.get("claims", [])
        if not isinstance(claims_data, list):
            raise ValueError(f"Failed to summarize source {source.id}: claims must be a list")
        evidence_entries: list[Evidence] = []
        for c in claims_data:
            evidence = Evidence(
                project_id=project.id,
                source_id=source.id,
                claim=c.get("claim", ""),
                support_text=c.get("support_text", ""),
                confidence=c.get("confidence", 0.5),
                tags=c.get("tags", []),
            )
            session.add(evidence)
            evidence_entries.append(evidence)
        return evidence_entries

    tasks = [process_source(s) for s in sources]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    failures: list[str] = []

    for batch in all_results:
        if isinstance(batch, Exception):
            failures.append(str(batch))
            continue
        all_evidence.extend(batch)

    if failures and not all_evidence:
        raise ValueError("Summarization failed for all sources: " + "; ".join(failures))

    session.commit()
    return all_evidence
