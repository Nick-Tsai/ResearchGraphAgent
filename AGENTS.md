# Repository Guidelines

## Project Structure

```
ResearchGraphAgent/
  backend/           # FastAPI server (Python 3.11+)
    app/
      main.py        # API endpoints & CORS config
      models.py      # SQLModel/SQLAlchemy ORM models
      schemas.py     # Pydantic request/response schemas
      db.py          # Database engine & session
      config.py      # Environment variables
      providers/     # Model & search provider implementations
      pipeline/      # Research pipeline stages
      tests/         # pytest test files
    .env             # Local overrides (not committed)
    .env.example     # Documented env template
    firecrawl_pool.json  # Firecrawl IP pool (not committed)
  frontend/          # Next.js App Router (TypeScript)
    app/
      page.tsx       # Home (topic input + recent projects)
      projects/[id]/ # Project detail (tabs: plan/sources/evidence/graph/review)
    lib/
      api.ts         # API client
      types.ts       # Shared TypeScript types
```

## Build, Test, and Development Commands

```bash
# Backend
cd backend
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
PYTHONPATH=. ./venv/bin/pytest app/tests/ -v   # 24 tests

# Frontend
cd frontend
npm install
npx next dev --port 3000
```

Backend uses SQLite (WAL mode) by default. Run with a single uvicorn worker — no `--reload` or `--workers`.

## Coding Style

- **Python**: 4-space indent, snake_case for functions/variables, PascalCase for classes, Pydantic v2 with `model_config = {"from_attributes": True}` for ORM mapping.
- **TypeScript**: 2-space indent (Next.js default), functional components with `"use client"` where needed, explicit types in `lib/types.ts`.
- All model JSON must be validated with Pydantic before writing to SQLite. Store `raw_model_output` for debugging.

## Testing

- Framework: pytest. Schema-level tests in `test_schemas.py`, integration tests in `test_api.py`, pipeline unit tests in `test_idps_planner.py`.
- Tests use in-memory SQLite (`sqlite://` with `StaticPool`), override `get_session` via `app.dependency_overrides`.
- Set `os.environ["MODEL_PROVIDER"] = "mock"` in test files before importing app code.

## Commit & Pull Request Guidelines

- Start commits with the affected area (e.g., `backend:`, `frontend:`, `pipeline:`).
- PR descriptions should note which milestone/feature is being addressed and how to test.

## Configuration

Environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_PROVIDER` | `mock` | LLM provider: `mock` / `deepseek` |
| `SEARCH_PROVIDER` | `mock` | Search: `mock` / `tavily` / `firecrawl` |
| `DEEPSEEK_API_KEY` | — | DeepSeek API key |
| `TAVILY_API_KEY` | — | Tavily API key (fallback for firecrawl) |

Firecrawl IP pool lives in `firecrawl_pool.json` (gitignored). Format: `{"instances": [{"url": "...", "api_key": "...", "weight": 1}]}`. Leave `api_key` empty for unauthenticated instances.
