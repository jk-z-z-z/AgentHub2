# Backend Architecture

## Core Direction

This backend is designed for an IM-style multi-agent collaboration platform where:

- each project group can enable one global `Manager Agent`
- planning is represented as one editable node graph per group
- each node belongs to one group and can be assigned to one member
- agent nodes can be auto-executed through the runtime packages
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
- `group_tasks`: DAG nodes, status editing, and confirmation flow
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

Application services for messages, groups, agent runs, task nodes, storage, and auth.

## Execution Model

### Group Scope

- a group contains human members and agent members
- agent members are backed by `AgentInstance`
- group can optionally enable one manager agent

### Plan Scope

- one editable DAG is maintained per group
- new planning requests patch nodes instead of creating unrelated graphs
- the DAG is editable in place from the UI

### Job Scope

- each node has one execution owner at a time
- the owner can be a user or an agent member
- if the owner is an agent, execution is performed by the runtime package

### Decision Flow

- user `@管家` triggers manager planning draft
- manager returns structured DAG draft and asks for confirmation
- only the draft creator can confirm and persist
- backend auto-assigns nodes by role to members when possible
- assigned agent nodes execute and append node-level events
- manager can review node outcomes and propose graph updates for unstarted nodes

## Runtime Packages

- `agent_runtime`: digital-worker replies and tool calls
- `manager_runtime`: manager replies, planning, and node work
- `bootstrap_runtime`: initialization and profile bootstrap
- `event_runtime`: event routing, event storage helpers, and reply writeback
- `ws_runtime`: websocket broadcast helpers
