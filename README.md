# Lakarra AI Operating System

A modular, multi-agent **AI Operating System** for the Lakarra business. Specialized
AI agents (CEO, Marketing, Content Analyst, Content Creator, Ad Manager, Product
Research, Card Designer, Software Tester) collaborate through a configurable
workflow engine to help run the business. This is **not** a chatbot.

> **Status: Phase 1 scaffold.** The architecture, interfaces and layers are in
> place with **mock implementations**. Business logic is intentionally not yet
> implemented — the goal is a clean foundation that can be extended incrementally.

## Architecture

| Layer | Location | Responsibility |
| --- | --- | --- |
| API | `backend/app/api` | FastAPI routes for agents, tasks, reports, approvals, workflows, etc. |
| Agents | `backend/app/agents` | Independent agents; each in its own directory, self-registered. |
| Tools | `backend/app/tools` | Common `BaseTool` interface + registry (TikTok, Canva, Playwright, …). |
| Memory | `backend/app/memory` | Shared memory + per-agent namespaces (in-memory default, Postgres target). |
| Models | `backend/app/models` | Pydantic domain models (JSON contracts) + SQLAlchemy ORM models. |
| Workflows | `backend/app/workflows` | LangGraph engine + configurable workflow definitions. |
| Services | `backend/app/services` | LLM provider abstraction (OpenAI/Anthropic/Gemini/mock). |
| Scheduler | `backend/app/scheduler` | Scheduled workflow skeleton (e.g. morning routine). |
| Database | `backend/app/database` | SQLAlchemy engine/session + Alembic migrations. |
| Dashboard | `frontend/app` | Next.js dashboard (Overview, Agents, Tasks, Reports, Content, Approvals, Analytics, Logs, Workflow History). |

Key design principles:

- **Add agents without touching existing ones** — create `app/agents/<name>/agent.py`,
  decorate the class with `@register_agent`, and import it in `app/agents/__init__.py`.
- **Structured JSON between agents** — agents exchange `AgentRequest` / `AgentResult`
  objects, not free-form text.
- **Provider-agnostic LLM** — business logic depends only on the `LLMProvider` interface.
- **No hardcoded workflows** — workflows are data (`WorkflowDefinition`) compiled into
  LangGraph graphs, with checkpoints, human-approval gates and retries.

## Running locally (development)

The backend defaults to an **in-memory** memory store and a **mock** LLM, so it
boots with zero external dependencies.

### Backend

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000  (docs at /docs)
```

Run checks:

```bash
./.venv/bin/ruff check app tests
./.venv/bin/pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev                                  # http://localhost:3000
```

### Docker (optional, includes Postgres + Redis)

```bash
docker compose up
```

## Configuration

Copy `backend/.env.example` → `backend/.env` and `frontend/.env.local.example` →
`frontend/.env.local` to adjust settings (memory backend, LLM provider, API URL).
