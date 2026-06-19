"""Mock model provider returning deterministic sample output per prompt type."""

import json
import re
from app.providers.base import ModelProvider


MOCK_IDPS_RESPONSE = {
    "problem_restatement": "Determine whether a research graph agent is useful, feasible, and worth building compared with existing research tools.",
    "constraints": [
        "The MVP should be buildable by one developer.",
        "The system should control LLM token cost.",
        "The first version should avoid fragile autonomous browsing."
    ],
    "assumptions": [
        "Users benefit from visual topic decomposition.",
        "Source-backed graph nodes are more useful than linear summaries.",
        "DeepSeek is good enough for bulk planning and summarization."
    ],
    "dimensions": [
        {
            "name": "User Workflow", "description": "How users move from vague topics to structured understanding.",
            "subquestions": ["What input does the user provide?", "What intermediate artifacts should the system show?", "Which actions should be interactive?"],
            "falsification_tests": ["Users prefer a normal chat interface over graph exploration.", "The graph adds complexity without improving decisions."]
        },
        {
            "name": "Evidence Quality", "description": "How the system retrieves, validates, and displays source-backed evidence.",
            "subquestions": ["Which sources should be trusted?", "How should unsupported claims be marked?", "How should contradictions be represented?"],
            "falsification_tests": ["Most generated nodes cannot be linked to credible sources.", "Contradiction detection produces mostly false positives."]
        },
        {
            "name": "Cost Control", "description": "How the system routes tasks between cheap and premium models.",
            "subquestions": ["Which tasks can DeepSeek handle?", "When should GPT-5.5 be used?", "How should token budgets be enforced?"],
            "falsification_tests": ["Premium review is required for nearly every useful output.", "Summarization consumes more tokens than expected."]
        }
    ],
    "initial_search_queries": [
        "research graph AI agent source backed summaries",
        "topic graph exploration tool AI research workflow",
        "LLM research agent citation graph architecture",
        "interactive knowledge graph research assistant"
    ],
    "risk_flags": [
        "The product may become a generic chatbot if the graph workflow is not enforced.",
        "Poor source extraction can undermine the entire system.",
        "The UI may look impressive before the research pipeline is reliable."
    ]
}

MOCK_SUMMARIZE_RESPONSE = json.dumps({
    "claims": [
        {"claim": "Graph-based research agents reduce hallucination by 47% compared to pure LLM output.", "support_text": "By structuring findings as graph nodes with explicit source edges, these systems achieve higher accuracy.", "confidence": 0.85, "tags": ["graph", "accuracy", "hallucination"]},
        {"claim": "Source-backed nodes increase user trust by 3.2x in controlled studies.", "support_text": "Users reported significantly higher confidence in results when each claim was linked to a verifiable source.", "confidence": 0.9, "tags": ["trust", "source", "verification"]},
        {"claim": "Interactive graph exploration enables serendipitous discovery that linear search misses.", "support_text": "Users exploring research graphs discovered 40% more relevant connections than keyword search alone.", "confidence": 0.75, "tags": ["discovery", "interactive", "exploration"]},
    ],
    "limitations": ["Computational cost of graph maintenance", "Difficulty with real-time updates"],
    "relevance_score": 0.85,
})

MOCK_CLASSIFY_RESPONSE = json.dumps({
    "assignments": {
        "User Workflow": ["ev-1", "ev-2"],
        "Evidence Quality": ["ev-3"],
        "Cost Control": [],
    }
})

def _mock_dimension_dsl(prompt: str) -> str:
    match = re.search(r'structured research notes for the dimension "([^"]+)"', prompt, re.IGNORECASE)
    dim_name = match.group(1) if match else "Research Dimension"
    safe = dim_name[:40]
    return f"""# Dimension: {safe}
[NODE]
Type: claim
Title: {safe} core claim
Summary: This dimension captures the strongest research-backed claim found for {safe}.
Evidence: ev-1, ev-2

[NODE]
Type: question
Title: Open question in {safe}
Summary: This dimension still has unresolved uncertainty that should be explored further.
Evidence: ev-2

[NODE]
Type: gap
Title: Evidence gap in {safe}
Summary: The current research material leaves at least one missing or weakly supported point in this dimension.
Evidence:
"""


MOCK_RELATION_DSL = """[EDGE]
From: User Workflow core claim
To: Open question in User Workflow
Relation: expands
Confidence: 0.70
Reason: The core claim leads to a specific unresolved design question.

[EDGE]
From: Evidence Quality core claim
To: Evidence gap in Cost Control
Relation: contradicts
Confidence: 0.65
Reason: Strong evidence quality requirements may conflict with a low-cost operating model.
"""

MOCK_EXPAND_RESPONSE = json.dumps({
    "subquestions": ["What are the key differences between graph and chat interfaces for research tasks?", "How do users transition between overview and detail views?", "What metrics best capture research exploration efficiency?"],
    "counterarguments": ["Some users may prefer linear reading for focused research.", "Graph complexity could overwhelm novice users."],
    "missing_evidence": ["Longitudinal studies on graph-based research tool adoption.", "A/B testing data comparing graph vs chat interfaces for specific research tasks."],
    "search_queries": ["graph based research tool user study 2024", "knowledge graph exploration vs chat research productivity"],
    "summary": "The node highlights a key tension in research tool design between structured graph exploration and natural chat interaction.",
})

MOCK_CHALLENGE_RESPONSE = json.dumps({
    "weak_assumptions": ["Assumes graph exploration is universally better without considering task type.", "Does not account for user expertise level affecting graph utility."],
    "missing_evidence": ["Studies on expert vs novice graph navigation performance.", "Evidence that graph exploration improves decision quality, not just discovery quantity."],
    "counterarguments": ["Linear document reading is proven effective for deep comprehension.", "Graph interfaces add cognitive load that may outweigh discovery benefits for simple topics."],
    "alternate_explanations": ["The 40% improvement could be due to novelty effect rather than inherent graph advantage."],
    "search_queries": ["cognitive load knowledge graph navigation study", "novelty effect new UI tool research productivity"],
    "summary": "While graph exploration shows promise, the evidence for universal superiority is mixed and depends on context.",
})

MOCK_PREMIUM_REVIEW_RESPONSE = json.dumps({
    "overall_assessment": "The research graph captures the key dimensions of building a research agent, with reasonable evidence coverage for User Workflow and Evidence Quality. Cost Control is under-explored.",
    "critical_issues": ["No quantitative budget analysis for LLM token costs across pipeline stages.", "Missing comparison with existing research tools (Semantic Scholar, Elicit, Consensus)."],
    "missing_dimensions": ["Scalability to large graphs", "Multi-user collaboration support"],
    "contradictions_to_resolve": ["Graph complexity concern in User Workflow vs assumed benefits of graph exploration."],
    "recommended_node_edits": [
        {"node_title": "Graph vs chat interface preference", "edit": "Add nuance: preference depends on task type (exploration vs fact-finding)."},
    ],
    "next_research_actions": ["Run cost simulation for typical research session token usage.", "Conduct competitive analysis of existing research tool interfaces."],
    "confidence_improvement": 0.2,
})

MOCK_ARTICLE_RESPONSE = json.dumps({
    "title": "Research Graph Agent: Consolidated Knowledge Map",
    "content": "This article integrates the plan, sources, evidence, graph, and review memories into a single narrative. It explains the core problem, summarizes the strongest evidence, surfaces contradictions, and closes with recommended next actions for the research agenda.",
})


class MockProvider(ModelProvider):
    @property
    def name(self) -> str:
        return "mock"

    async def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        prompt_lower = prompt.lower()

        if "idps-style research plan" in prompt_lower or "planning module" in prompt_lower:
            return json.dumps(MOCK_IDPS_RESPONSE)
        if "summarize this source" in prompt_lower or '"claims"' in prompt_lower:
            return MOCK_SUMMARIZE_RESPONSE
        if "structured research notes for the dimension" in prompt_lower:
            return _mock_dimension_dsl(prompt)
        if "connecting a research graph across dimensions" in prompt_lower:
            return MOCK_RELATION_DSL
        if "expand this graph node" in prompt_lower:
            return MOCK_EXPAND_RESPONSE
        if "challenge this graph node" in prompt_lower:
            return MOCK_CHALLENGE_RESPONSE
        if "premium review model" in prompt_lower or "compressed graph" in prompt_lower:
            return MOCK_PREMIUM_REVIEW_RESPONSE
        if "article synthesis module" in prompt_lower or "structured memories" in prompt_lower:
            return MOCK_ARTICLE_RESPONSE
        return MOCK_SUMMARIZE_RESPONSE
