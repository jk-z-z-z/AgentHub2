# Backend Architecture

## Core Direction

This backend is designed for an IM-style multi-agent collaboration platform where:

- each project group can enable one global `Manager Agent`
- planning is represented as one mutable DAG run per group
- each node is assigned to one group member (`user` or `agent`)
- agent nodes can be auto-executed through LLM runtime
- manager planning is confirm-first, then persisted

## Module Responsibilities

### `api/`

FastAPI routers and endpoint contracts.

Current slice:

- `health`: service health check

Planned slices:

- `groups`: collaboration container
- `members`: group participants
- `agent_profiles`: reusable agent templates
- `agents`: agent instance and workspace management
- `group_tasks`: DAG run, nodes, events, and confirmation flow
- `messages`: user chat and manager-triggered planning

### `core/`

Application settings and lifecycle wiring.

### `db/`

Persistence package.

Planned responsibilities:

- database engine and session management
- ORM models
- migration entrypoint

### `schemas/`

Request and response contracts for API consumers.

### `services/`

Business logic and external integration boundaries.

Key services:

- `ManagerPlanningService`: @manager context build and plan draft generation
- `GroupTaskService`: DAG upsert, assignment, execution, and event persistence
- `AIService`: model call boundary

## Execution Model

### Group Scope

- a group contains human members and agent members
- agent members are backed by `AgentInstance`
- group can optionally enable one manager agent profile

### Plan Scope

- one active DAG run is maintained per group
- new planning requests patch remaining nodes instead of creating unrelated graphs
- the DAG is editable in place from the UI

### Job Scope

- each node has one execution owner at a time
- the owner can be a user or an agent member
- if the owner is an agent, execution is performed by backend LLM runtime

### Decision Flow

- user `@管家` triggers manager planning draft
- manager returns structured DAG draft and asks for confirmation
- only the draft creator can confirm and persist
- backend auto-assigns nodes by role to members when possible
- assigned agent nodes execute and append node-level events
- manager can review node outcomes and propose graph updates for unstarted nodes

## ACP External Runner (Codex / Claude Code)

AgentHub can optionally delegate *node execution* to external ACP-compatible runners (Codex / Claude Code),
similar to QwenPaw's ACP integration.

- Provider model: `app/models/acp_provider.py` (table: `acp_providers`)
- Provider API: `app/api/acp_providers.py` (`GET /api/v1/acp-providers`)
- Minimal stdio ACP client: `app/services/acp_runner/acp_stdio.py`
- Node execution hook: `app/services/group_task/node_service.py` uses ACP when the assignee agent has
  `engine_type` formatted as `acp:<provider_type>` (e.g. `acp:codex`, `acp:claude_code`)

Environment configuration:
- `AGENTHUB_ACP_CODEX_COMMAND` defaults to `npx -y @zed-industries/codex-acp`
- `AGENTHUB_ACP_CLAUDE_COMMAND` defaults to `python -m claude_code_acp`

This is minimal & safe-by-default: ACP permission requests are rejected and filesystem/terminal calls are disabled.
