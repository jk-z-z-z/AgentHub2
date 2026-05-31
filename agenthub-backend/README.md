# AgentHub Backend

`AgentHub Backend` is the server-side foundation for an enterprise-deployable multi-agent collaboration platform.

This initial scaffold uses:

- `uv` for project and dependency management
- `FastAPI` for HTTP APIs
- `AgentScope` as the agent runtime foundation
- `SQLite` as the planned first-stage storage

## Project Structure

```text
agenthub-backend/
├── app/                      # AgentHub2-style FastAPI application package
│   ├── api/                  # API routers
│   ├── common/               # Shared helpers
│   ├── core/                 # Settings
│   ├── db/                   # Engine and base metadata
│   ├── models/               # SQLAlchemy models (one file per table)
│   ├── schemas/              # Pydantic request/response models
│   ├── services/             # Domain services
│   └── main.py               # FastAPI entrypoint
├── docs/                     # Architecture, roadmap, and database design
└── pyproject.toml
```

## Quick Start

```bash
cd /Users/youtao/Projects/AgentHub-agentscope/agenthub-backend
uv sync
uv run uvicorn app.main:app --reload
```

## Configure AI Chat (AgentScope)

Create `agenthub-backend/.env`:

```bash
AGENTHUB_OPENAI_API_KEY=your_key
# optional
AGENTHUB_OPENAI_BASE_URL=https://api.openai.com/v1
AGENTHUB_OPENAI_MODEL=gpt-4.1-mini
```

Then call:

- `POST /api/v1/ai/chat` (requires `Authorization: Bearer <token>`)

## Seed Demo Data

Start backend first, then run:

```bash
cd /Users/youtao/Projects/AgentHub-agentscope/agenthub-backend
uv run python scripts/seed_demo.py --base-url http://127.0.0.1:8000/api/v1
```

## Current Scope

This scaffold currently includes:

- AgentHub2-style app structure
- health endpoint and API v1 routers
- SQLite persistence with configuration CRUD and message APIs
- architecture and phase planning docs

## Next Build Targets

- group chat and membership APIs
- plan creation and DAG editing APIs
- node/job execution lifecycle with AgentScope workers
- streaming event API for node-level progress
- ACP-compatible external runner integration
