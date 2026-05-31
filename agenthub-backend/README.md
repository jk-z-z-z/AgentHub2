# AgentHub Backend

`AgentHub Backend` is the server-side foundation for a multi-tenant group collaboration + agent execution platform.

Current stack:

- `uv` for project and dependency management
- `FastAPI` for HTTP APIs
- `AgentScope` as the agent runtime foundation
- `SQLite` as current storage

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

## Configure AI Runtime

Create `agenthub-backend/.env`:

```bash
AGENTHUB_OPENAI_API_KEY=your_key
# optional
AGENTHUB_OPENAI_BASE_URL=https://api.openai.com/v1
AGENTHUB_OPENAI_MODEL=gpt-4.1-mini
```

Then you can call:

- `POST /api/v1/ai/chat` (requires `Authorization: Bearer <token>`)

## Seed Demo Data

Start backend first, then run:

```bash
cd /Users/youtao/Projects/AgentHub-agentscope/agenthub-backend
uv run python scripts/seed_demo.py --base-url http://127.0.0.1:8000/api/v1
```

## Current Capabilities

- Auth: admin bootstrap and token-based authentication
- Groups: create/list/delete groups (`personal` / `project`) with member constraints
- Members: add/remove user or agent members
- Messages: send/list messages, websocket broadcast, `@管家` trigger path
- Manager planning: draft DAG by LLM, creator-only confirmation, then upsert to group task run
- Group tasks: run/node/event persistence, node assignment, agent-node execution events
- Agents: profile templates + agent instances + per-agent workspace bootstrap
- Tools/MCP: builtin tools registry + agent tool toggles + MCP metadata CRUD
- Memory: short-term context + long-memory compression pipeline integration

## Reply Architecture

Current chat reply pipeline uses layered design patterns:

- Factory: `app/services/group_ai_reply/agent_factory.py` creates role agents (`Manager` / `Assistant`)
- Strategy: `app/services/group_ai_reply/strategies/*` decides reply branch (`personal`, `@manager`, `@agent`, `noop`)
- Executor: `app/services/group_ai_reply/reply_executor.py` is the single reply entry and emits `reply.failed` on errors
- Memory Strategy: `app/services/group_ai_reply/memory/*` provides context loading for personal vs project scenes

Flow:

`message_service.create_message_and_trigger_ai(...)`
-> `ReplyExecutor.execute(ctx)`
-> `GroupAiReplyEngine.handle(ctx)`
-> matched strategy
-> role agent + memory strategy
-> `ai_chat(...)` / manager planning tools
-> persisted AI message

## API Docs

- Runtime docs: `http://127.0.0.1:8000/docs`
- Snapshot spec file: `/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/openapi.json`

## Notes

- `group` is treated as project container in current design.
- One group keeps one active planning graph that is updated incrementally.
