# DeepSeek Coding Harness for Research Graph Agent

Use this harness before asking DeepSeek to write code. Paste the "Coding Agent Prompt" section into DeepSeek, attach or include `research-graph-agent.md`, and instruct it to complete only the active milestone.

The purpose of this harness is to prevent DeepSeek from overbuilding, skipping validation, or creating a fragile autonomous agent before the deterministic research pipeline works.

## 1. Operating Mode

DeepSeek should act as a disciplined implementation agent.

It must:

- read `research-graph-agent.md` before coding
- implement one milestone at a time
- keep changes small and testable
- prefer explicit pipeline functions over open-ended agents
- use typed schemas for model outputs
- validate JSON from all model calls
- use mock providers before real API providers
- avoid premium model calls unless explicitly requested
- report what it changed and how to run it

It must not:

- build a landing page
- build a general chatbot as the main interface
- call GPT-5.5 automatically
- implement browser automation before normal search/extraction works
- create a complex multi-agent system in the MVP
- hide model failures from the user
- make source-less claim nodes without marking them as gaps

## 2. Source Documents

DeepSeek should treat these files as controlling instructions:

```text
research-graph-agent.md
deepseek-coding-harness.md
```

If the two documents conflict, follow `deepseek-coding-harness.md` for implementation process and `research-graph-agent.md` for product requirements.

## 3. Active Milestone

Default active milestone:

```text
Milestone 1 + Milestone 2 only
```

Scope:

- backend project creation
- SQLite persistence
- IDPS planner with a mock model provider
- optional DeepSeek provider behind environment variables
- frontend topic input
- project detail page showing IDPS dimensions and subquestions

Out of scope for the first coding pass:

- web search
- page extraction
- React Flow graph rendering
- node expansion
- challenge mode
- premium review
- LangGraph
- Redis/Celery
- Playwright

## 4. Implementation Strategy

Build a small vertical slice:

```text
Create project -> run IDPS planner -> save plan -> display plan
```

Recommended order:

1. Create backend skeleton.
2. Define schemas and database models.
3. Implement mock model provider.
4. Implement optional DeepSeek provider.
5. Implement IDPS planner service.
6. Implement API endpoints.
7. Add backend tests.
8. Create frontend skeleton.
9. Add topic input.
10. Add project detail page.
11. Add API client.
12. Verify end-to-end with mock provider.

## 5. Backend Requirements

Use:

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy or SQLModel
- SQLite for local persistence
- pytest for tests

Backend endpoints for first pass:

```text
POST /api/projects
GET /api/projects/{project_id}
POST /api/projects/{project_id}/run-idps
GET /api/projects/{project_id}/plan
```

Expected behavior:

- `POST /api/projects` creates a project from `{ "topic": "..." }`
- `POST /api/projects/{project_id}/run-idps` generates and saves an IDPS plan
- mock provider returns deterministic sample JSON
- DeepSeek provider is used only when configured
- invalid model JSON returns a clear API error

## 6. Frontend Requirements

Use:

- Next.js
- TypeScript
- functional components
- simple CSS or existing styling conventions

First screen:

- topic input
- create project button
- recent projects list if available

Project page:

- topic
- status
- problem restatement
- constraints
- assumptions
- dimensions
- subquestions
- falsification tests
- initial search queries
- risk flags
- run IDPS button if no plan exists

Keep the UI functional and dense. Do not make a marketing page.

## 7. Environment Variables

Use these names:

```text
MODEL_PROVIDER=mock|deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DATABASE_URL=sqlite:///./research_graph_agent.db
```

If `MODEL_PROVIDER` is missing, default to `mock`.

## 8. Data Schemas

The IDPS plan must validate against this shape:

```json
{
  "problem_restatement": "string",
  "constraints": ["string"],
  "assumptions": ["string"],
  "dimensions": [
    {
      "name": "string",
      "description": "string",
      "subquestions": ["string"],
      "falsification_tests": ["string"]
    }
  ],
  "initial_search_queries": ["string"],
  "risk_flags": ["string"]
}
```

Use Pydantic validation before saving.

## 9. Mock IDPS Output

The mock provider should return realistic data, not placeholder lorem ipsum.

Example topic:

```text
Should I build a research graph agent?
```

Example mock response:

```json
{
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
      "name": "User Workflow",
      "description": "How users move from vague topics to structured understanding.",
      "subquestions": [
        "What input does the user provide?",
        "What intermediate artifacts should the system show?",
        "Which actions should be interactive?"
      ],
      "falsification_tests": [
        "Users prefer a normal chat interface over graph exploration.",
        "The graph adds complexity without improving decisions."
      ]
    },
    {
      "name": "Evidence Quality",
      "description": "How the system retrieves, validates, and displays source-backed evidence.",
      "subquestions": [
        "Which sources should be trusted?",
        "How should unsupported claims be marked?",
        "How should contradictions be represented?"
      ],
      "falsification_tests": [
        "Most generated nodes cannot be linked to credible sources.",
        "Contradiction detection produces mostly false positives."
      ]
    },
    {
      "name": "Cost Control",
      "description": "How the system routes tasks between cheap and premium models.",
      "subquestions": [
        "Which tasks can DeepSeek handle?",
        "When should GPT-5.5 be used?",
        "How should token budgets be enforced?"
      ],
      "falsification_tests": [
        "Premium review is required for nearly every useful output.",
        "Summarization consumes more tokens than expected."
      ]
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
```

## 10. Testing Requirements

Add tests before declaring the milestone complete.

Minimum backend tests:

- project creation succeeds
- empty topic is rejected
- mock IDPS plan validates
- invalid IDPS JSON is rejected
- project plan can be saved and fetched

Optional frontend checks:

- topic input renders
- project page renders mock plan data
- API client handles loading and error states

## 11. Done Criteria

The first coding pass is done only when:

- backend starts without errors
- frontend starts without errors
- user can create a project
- user can run IDPS planning
- IDPS plan is saved
- frontend displays the plan
- mock provider works without API keys
- DeepSeek provider is configurable but not required
- tests pass or any failing tests are clearly explained

## 12. Coding Agent Prompt

Paste this into DeepSeek:

```text
You are the coding agent for a project called Research Graph Agent.

Before coding, read and follow these two documents:

1. research-graph-agent.md
2. deepseek-coding-harness.md

Your active scope is Milestone 1 + Milestone 2 only:

- backend project creation
- SQLite persistence
- IDPS planner with a mock model provider
- optional DeepSeek provider behind environment variables
- frontend topic input
- project detail page showing IDPS dimensions and subquestions

Do not implement web search, page extraction, React Flow graph rendering, node expansion, challenge mode, premium review, LangGraph, Redis/Celery, or Playwright yet.

Build a small vertical slice:

Create project -> run IDPS planner -> save plan -> display plan

Implementation rules:

- Use FastAPI, Pydantic, SQLite, and pytest for the backend.
- Use Next.js and TypeScript for the frontend.
- Default MODEL_PROVIDER to mock.
- Use DeepSeek only if MODEL_PROVIDER=deepseek and DEEPSEEK_API_KEY is present.
- Validate all model JSON with Pydantic before saving.
- Store raw model output for debugging.
- Keep the UI dense and functional, not marketing-like.
- Add tests for schema validation and project/plan endpoints.
- Report changed files, run commands, and remaining gaps when finished.

Start by inspecting the repo. If no app exists, create:

research-graph-agent/backend
research-graph-agent/frontend

Then implement only the active milestone.
```

## 13. Review Prompt After DeepSeek Finishes

After DeepSeek finishes, run this review prompt with GPT-5.5 or another strong model:

```text
Review this implementation of Research Graph Agent Milestone 1 + 2.

Focus on:
- whether the implementation stayed within scope
- whether model JSON is validated before persistence
- whether mock provider works without keys
- whether DeepSeek provider is safely gated by env vars
- whether API endpoints match the harness
- whether tests cover the critical paths
- whether the frontend is a working app rather than a landing page

List blocking issues first with file references.
Then list non-blocking improvements.
Do not rewrite the app unless necessary.
```

