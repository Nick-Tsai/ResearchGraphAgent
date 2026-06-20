# Research Graph Agent — Integration Plan

## Environment Summary

| Key | Value |
|---|---|
| Domain | `www.zhimingjun.com` |
| Sub-path | `/research/` |
| Web Server | Caddy (existing, shared with other projects) |
| Deployment | Docker Compose (3 services: backend + frontend, no nginx) |
| Backend Port | 8000 (internal), 8001 (host) |
| Frontend Port | 3000 (internal), 3001 (host) |
| Database | SQLite (WAL mode), persisted at `./data/` |
| LLM | DeepSeek V4 Flash |
| Search | Firecrawl self-hosted IP pool (25 nodes) |

## Architecture

```
Browser
  → Caddy (:80/:443)
    → /research/*       → localhost:3001 (Next.js frontend, basePath=/research)
    → /research/api/*   → localhost:8001 (FastAPI backend, root_path=/research)
```

## Environment Variables

### Backend (`backend/.env`)
| Variable | Default | Required |
|---|---|---|
| MODEL_PROVIDER | mock | No |
| DEEPSEEK_API_KEY | — | Yes (production) |
| SEARCH_PROVIDER | mock | No |
| TAVILY_API_KEY | — | No (fallback) |
| CORS_ORIGINS | http://localhost:3000 | No |
| DATABASE_URL | sqlite:///./research_graph_agent.db | No |
| ROOT_PATH | /research | Yes (production) |

### Frontend (`docker-compose.yml`)
| Variable | Value |
|---|---|
| NODE_ENV | production |
| NEXT_PUBLIC_BASE_PATH | /research |
| NEXT_PUBLIC_API_BASE | /research/api |

## Task Checklist

- [x] Fix hardcoded `127.0.0.1:8000/api` in page.tsx
- [x] Fix hardcoded CORS origins in main.py
- [x] `ROOT_PATH` via FastAPI constructor + env var
- [x] `NEXT_PUBLIC_BASE_PATH` at Docker build time
- [x] `NEXT_PUBLIC_API_BASE` at Docker build time
- [x] Docker China mirrors (m.daocloud.io, Tsinghua pip, npmmirror)
- [x] API client fallback to env var
- [ ] Add `CORS_ORIGINS` to docker-compose.yml
- [ ] Server `git pull && docker compose up --build -d`

## Caddy Configuration

```
www.zhimingjun.com {
    handle /research/api* {
        reverse_proxy localhost:8001
    }
    handle /research* {
        reverse_proxy localhost:3001
    }
    # ... existing projects ...
}
```

## Git

Remote: `git@github.com:Nick-Tsai/ResearchGraphAgent.git`

Commit convention: `area: description` (e.g., `fix:`, `feat:`, `docs:`)
