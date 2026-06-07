# Backend Architecture

## Core Direction

This backend is an IM-style multi-agent collaboration platform with two parallel concerns:

- message-driven collaboration between users, agents, and the manager
- project-scoped runtime execution against shared code workspaces

The current codebase assumes:

- each project group can enable one global `Manager Agent`
- planning is represented as one editable node graph per group
- each node belongs to one group and can be assigned to one member
- agent node execution is event-driven and manager-reviewed
- each `project` group owns one runtime workspace backed by shared project code

## Module Responsibilities

### `api/`

FastAPI routers and endpoint contracts.

Current slices:

- `auth`: login and current-user identity
- `users`: user profile and personal markdown assets
- `groups`: collaboration containers and project memory compressor endpoints
- `members`: user and agent membership management
- `messages`: chat write path and event feed queries
- `group_tasks`: editable DAG, node status transitions, and execution requests
- `agent_profiles`: reusable agent templates and template files
- `agents`: agent instances, workspace files, tools, skills, and bootstrap flows
- `tools`: builtin tool registry
- `mcps`: MCP metadata CRUD
- `acp_providers`: ACP executor metadata and toggles
- `project_code`: read-only access to shared project code
- `workspaces`: project workspace lookup and snapshot creation
- `executions`: sandbox command jobs
- `deployments`: deployment pipeline jobs and retries
- `ai`: direct chat test endpoint
- `ws_groups`: group WebSocket broadcast endpoint

### `core/`

Application settings, security helpers, and lifecycle wiring.

### `db/`

Persistence package.

Current responsibilities:

- SQLAlchemy engine and session management
- ORM base mixins and models
- development-first schema creation from `Base.metadata`

### `schemas/`

Pydantic request and response contracts, including runtime job payloads for workspaces, executions, and deployments.

### `services/`

Application services for messages, groups, memberships, agent/profile storage, task nodes, project workspaces, runtime jobs, and auth.

## Execution Model

### Group Scope

- a group contains human members and agent members
- agent members are backed by `AgentInstance`
- group can optionally enable one manager agent

### Plan Scope

- one editable DAG is maintained per group
- new planning requests patch nodes instead of creating unrelated graphs
- the DAG is editable in place from the UI

### Workspace Scope

- every `project` group gets one workspace row
- the workspace source root points at `projects/{group_id}/shared/code`
- snapshot creation copies the current source tree into `workspaces/{workspace_id}/snapshots/{snapshot_id}`

### Job Scope

- each DAG node has one execution owner at a time
- the owner can be a user or an agent member
- if the owner is an agent, execution is requested by event, dispatched by the runtime, and then reviewed by manager
- project command execution is modeled as `execution_jobs` plus `sandbox_runs`
- project deployment is modeled as `deployment_jobs` plus `sandbox_runs`

### Decision Flow

- user `@管家` triggers manager planning draft
- manager returns structured DAG draft and asks for confirmation
- only the draft creator can confirm and persist
- backend auto-assigns nodes by role to members when possible
- `manager.node_execute` writes a node execution request event
- dispatcher reads the event, invokes the assigned agent, and records execution trace events
- the agent writes `task.completed` or `task.failed`
- manager receives completion events, reviews the node, and updates node state or DAG when needed
- project-scoped tools can also create workspace snapshots, sandbox runs, execution jobs, or deployment jobs directly for the current project

## Runtime Packages

- `agent_runtime`: digital-worker replies and tool calls
- `manager_runtime`: manager replies, planning, and node work
- `bootstrap_runtime`: initialization and profile bootstrap
- `event_runtime`: event routing, event storage helpers, and reply writeback
- `memory_runtime`: project memory compression and token estimation helpers
- `ws_runtime`: WebSocket broadcast helpers
