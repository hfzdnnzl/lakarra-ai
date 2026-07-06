# AGENTS.md

Lakarra AI Operating System — a modular multi-agent platform. Backend:
Python/FastAPI/LangGraph (`backend/`). Frontend: Next.js dashboard (`frontend/`).
See `README.md` for the full architecture and standard run/lint/test commands.

## Cursor Cloud specific instructions

### Services

- **Backend API** (`backend/`): FastAPI on port `8000`. Dev server:
  `./.venv/bin/uvicorn app.main:app --reload` (run from `backend/`). OpenAPI docs at
  `/api` is the route prefix; interactive docs at `http://localhost:8000/docs`.
- **Frontend dashboard** (`frontend/`): Next.js on port `3000`. Dev server:
  `npm run dev` (run from `frontend/`). It calls the backend at
  `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api`), so start the
  backend first.

### Lint / test / build

- Backend lint: `./.venv/bin/ruff check app tests` (from `backend/`).
- Backend tests: `./.venv/bin/pytest` (from `backend/`).
- Frontend lint: `npm run lint`; production build check: `npm run build` (from `frontend/`).

### Non-obvious caveats

- **System dependency:** creating the backend virtualenv requires the
  `python3.12-venv` apt package (installed during environment setup). If
  `python3 -m venv` fails with an `ensurepip`/venv error on a fresh VM, install it:
  `sudo apt-get install -y python3.12-venv`.
- **Zero external services needed for dev.** The backend defaults to an in-memory
  memory store (`MEMORY_BACKEND=in_memory`) and a mock LLM (`LLM_PROVIDER=mock`), so
  it boots with no database, Redis, or API keys. Postgres/Redis (via
  `docker-compose.yml`) and the SQLAlchemy/Alembic layer are the Phase 2 target and
  are **not** required to run or test the app.
- **In-memory state resets on backend restart.** Tasks, reports, approvals and
  workflow-run history live in process; restart `uvicorn` to get a clean slate.
- **Workflow thread ids matter.** The LangGraph engine uses a shared `MemorySaver`
  checkpointer and the workflow `steps` field uses an additive reducer. Reusing the
  same `thread_id` across separate runs accumulates state (steps get appended). Each
  independent run should pass a unique `thread_id`; the dashboard already does this.
  The human-approval flow deliberately reuses one `thread_id` so a paused run can be
  resumed via `POST /api/workflows/{name}/resume`.
- **pytest rootdir:** tests import the `app` package via `pythonpath = ["."]` set in
  `backend/pyproject.toml`; run pytest from the `backend/` directory.
- **Adding an agent (no edits to existing agents):** create
  `backend/app/agents/<name>/agent.py` with a class decorated by `@register_agent`,
  then import it in `backend/app/agents/__init__.py`.
