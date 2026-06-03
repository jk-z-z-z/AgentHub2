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
- AI routing: `group_ai_reply` decides whether to call `bootstrap_runtime`, `agent_runtime`, or `manager_runtime`
- Manager planning: draft DAG by LLM, creator-only confirmation, then upsert to group task run
- Group tasks: run/node/event persistence, graph snapshots, node assignment, agent-node execution events, final summaries
- Agents: profile templates + agent instances + per-agent workspace bootstrap
- Tools/MCP: builtin tools registry + agent tool toggles + MCP metadata CRUD
- Memory: short-term context + long-memory compression pipeline integration

## Runtime Architecture

Current runtime stack uses three single-facade packages:

- `app/agent_runtime.invoke_agent()` handles digital-worker replies, tool calls, message persistence, and process events
- `app/manager_runtime.invoke_manager()` handles manager replies, planning, tool execution, and message persistence
- `app/bootstrap_runtime.invoke_bootstrap()` handles bootstrap initialization messages and process events

Flow:

`message_service.create_message_and_trigger_ai(...)`
-> `group_ai_reply.handle_group_ai_reply(...)`
-> `bootstrap_runtime / agent_runtime / manager_runtime`
-> runtime-specific persistence and event logging

## API Docs

- Runtime docs: `http://127.0.0.1:8000/docs`
- Snapshot spec file: `/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/openapi.json`

## Notes

- `group` is treated as project container in current design.
- One group keeps one active planning graph that is updated incrementally.
- `group_task/orchestration` contains task-graph snapshot, assignment, replanning, receipt, and finalization helpers.
