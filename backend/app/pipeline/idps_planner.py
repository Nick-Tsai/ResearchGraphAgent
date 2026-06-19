"""IDPS planner: decomposes a topic into a structured research plan."""

import json
from pydantic import ValidationError
from sqlmodel import Session
from app.models import Project, IDPSPlan
from app.schemas import IDPSPlanSchema
from app.providers.base import ModelProvider

IDPS_PROMPT_TEMPLATE = """\
You are the planning module for a research graph agent.

Given the user topic, produce a compact IDPS-style research plan as strict JSON.

You MUST return a JSON object with EXACTLY these keys (no other names, no renames):

{{
  "problem_restatement": "One sentence restating the real research question.",
  "constraints": ["Fixed or inferred limits."],
  "assumptions": ["Important assumptions that may be false."],
  "dimensions": [
    {{
      "name": "Dimension Name",
      "description": "What this dimension covers.",
      "subquestions": ["Question 1", "Question 2"],
      "falsification_tests": ["What evidence would weaken this?"]
    }}
  ],
  "initial_search_queries": ["Query 1", "Query 2"],
  "risk_flags": ["Known ambiguity, controversy, or high-risk area."],
  "audience_level": "elementary|middle|high|college"
}}

IMPORTANT — Before generating the plan, analyze the user's question:
- If the user uses simple words and seems young → audience_level = "elementary"
- If the user seems like a middle/high school student → audience_level = "middle" or "high"
- If the user uses technical jargon and academic language → audience_level = "college"
- Default to "high" if unsure.

Requirements:
- problem_restatement: single sentence.
- constraints: 2-5 fixed limits.
- assumptions: 2-5 key assumptions.
- dimensions: 4-8 dimensions, each with 2-5 subquestions and 1-3 falsification_tests.
- initial_search_queries: 8-15 targeted search queries.
- risk_flags: 3-7 ambiguity, controversy, or high-risk areas.
- Return ONLY valid JSON, no markdown fences, no extra text.

User topic:
{topic}"""


async def run_idps(project: Project, provider: ModelProvider, session: Session) -> IDPSPlan:
    """Run IDPS planning for a project and persist the plan."""
    prompt = IDPS_PROMPT_TEMPLATE.format(topic=project.topic)
    raw_output = await provider.complete(prompt)

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}\nRaw output: {raw_output[:500]}")

    try:
        plan_data = IDPSPlanSchema.model_validate(parsed)
    except ValidationError as e:
        raise ValueError(f"Model output failed schema validation: {e}\nParsed data: {parsed}") from e

    plan = IDPSPlan(
        project_id=project.id,
        problem_restatement=plan_data.problem_restatement,
        constraints=plan_data.constraints,
        assumptions=plan_data.assumptions,
        dimensions=[d.model_dump() for d in plan_data.dimensions],
        initial_search_queries=plan_data.initial_search_queries,
        risk_flags=plan_data.risk_flags,
        raw_model_output=raw_output,
        provider_used=provider.name,
    )
    session.add(plan)
    project.status = "running"
    if "audience_level" in parsed:
        project.audience_level = parsed["audience_level"]
    session.add(project)
    session.commit()
    session.refresh(plan)
    return plan
