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
│   ├── api/                  # HTTP routers
│   ├── agent_runtime/        # Digital worker runtime
│   ├── bootstrap_runtime/    # Bootstrap runtime
│   ├── event_runtime/        # Message/event orchestration
│   ├── manager_runtime/      # Manager runtime
│   ├── memory_runtime/       # Memory token estimation and config helpers
│   ├── ws_runtime/           # WebSocket broadcast helpers
│   ├── common/               # Shared helpers
│   ├── core/                 # Settings
│   ├── db/                   # Engine and base metadata
│   ├── models/               # SQLAlchemy models (one file per table)
│   ├── schemas/              # Pydantic request/response models
│   ├── services/             # Thin domain services
│   └── main.py               # FastAPI entrypoint
├── docs/                     # Architecture, roadmap, and database design
└── pyproject.toml
```

## Quick Start

```bash
cd agenthub-backend
uv sync
uv run uvicorn app.main:app --reload
```

If port `8000` is already in use, choose another port:

```bash
uv run uvicorn app.main:app --reload --port 8012
```

> 开发模式下启动会直接重建 SQLite 表结构并重新种子化基础数据；如果你要保留本地数据，先切换到非 `local/dev` 环境。

## Configure AI Runtime

Create `agenthub-backend/.env` from `.env.example` and fill in your local values:

```bash
cp .env.example .env
```

Then you can call:

- `POST /api/v1/ai/chat` (requires `Authorization: Bearer <token>`)

## Seed Demo Data

Start backend first, then run:

```bash
cd agenthub-backend
uv run python scripts/seed_demo.py --base-url http://127.0.0.1:8000/api/v1
```

## Current Capabilities

- Auth: admin bootstrap and token-based authentication
- Groups: create/list/delete groups (`personal` / `project`) with member constraints
- Members: add/remove user or agent members
- Messages: send/list messages, websocket broadcast, `@管家` trigger path
- AI routing: `event_runtime` decides whether to call `bootstrap_runtime`, `agent_runtime`, or `manager_runtime`
- Manager planning: draft DAG by LLM, creator-only confirmation, then update the group graph
- Group tasks: node graph persistence, graph snapshots, node assignment, node execution request events, manager review, final summaries
- Agents: profile templates + agent instances + per-agent workspace bootstrap
- Tools/MCP: builtin tools registry + agent tool toggles + MCP metadata CRUD
- Memory: short-term context + token estimation helpers

## Runtime Architecture

Current runtime stack uses four single-facade packages:

- `app/agent_runtime.invoke_agent()` handles digital-worker replies, tool calls, message persistence, and trace events
- `app/manager_runtime.invoke_manager()` handles manager replies, graph editing, node review, and trace events
- `app/bootstrap_runtime.invoke_bootstrap()` handles bootstrap initialization messages and process events
- `app.memory_runtime` currently provides memory config and token estimation helpers

Flow:

`message_service.create_message_and_trigger_ai(...)`
-> `agent_runtime.message_store.create_message(...)`
-> `event_runtime.dispatcher.dispatch_message_event_chain(...)`
-> `event_runtime.handlers.message` / `event_runtime.handlers.task`
-> `bootstrap_runtime / agent_runtime / manager_runtime`
-> runtime-specific persistence, event logging, and node review

## API Docs

- Runtime docs: `http://127.0.0.1:8000/docs`
- Snapshot spec file: `/Users/youtao/Projects/AgentHub-agentscope/agenthub-backend/openapi.json`

## Notes

- `group` is treated as project container in current design.
- One group keeps one active editable graph that is updated incrementally.
- `group_task_service` contains node graph, assignment, state transitions, and review helpers.
- `memory_runtime` contains memory config and token estimation helpers.
