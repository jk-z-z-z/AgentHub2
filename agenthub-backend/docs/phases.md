# Delivery Phases

## Phase 1: Foundation

Goal: establish a clean backend skeleton and shared data model.

Modules:

- `core`: config and lifecycle
- `api/health`: service health endpoint
- `db`: persistence placeholder
- `schemas`: request and response placeholder
- `services`: orchestration and runtime placeholder
- `docs`: architecture and roadmap

Deliverables:

- runnable FastAPI app
- `uv`-managed project
- health check endpoint
- documented module boundaries

## Phase 2: Collaboration Domain

Goal: build the collaboration configuration center and basic IM message persistence.

Modules:

- `api/groups`
- `api/members`
- `api/messages`
- `api/tools`
- `api/mcps`
- `api/agent_profiles`
- `api/agents`
- `services/group_service`
- `services/agent_instance_service`

Deliverables:

- create groups
- create user members and agent members
- read builtin tools and manage MCP metadata
- create agent profiles as template files
- instantiate agents from profiles and own workspace
- send and store chat messages through HTTP
- establish the first SQLite persistence layer

## Phase 3: Group Planning And DAG Editing

Goal: let the manager agent create and revise plans.

Modules:

- `api/group_tasks`
- `services/group_task_service`
- `manager_runtime`

Deliverables:

- create and update group task DAG nodes and edges
- support manager draft -> user confirm -> graph update
- support in-place DAG edits and reassignment

## Phase 4: Node Execution Runtime

Goal: drive node execution through the event dispatcher and runtime packages.

Modules:

- `api/group_tasks`
- `services/group_task_service`
- `agent_runtime`

Deliverables:

- write node execution request events
- dispatch assigned agents from events
- store child-agent completion and manager review events
- expose node events API for frontend polling

## Phase 5: Replan And Governance

Goal: support manager-led follow-up decisions and safe replanning.

Modules:

- `services/group_task_service`
- `api/group_tasks`

Deliverables:

- manager can generate structured plan draft from recent context
- only draft creator can confirm and落库
- new planning requests update existing active graph

## Phase 6: Production Hardening

Goal: improve reliability and enterprise readiness.

Modules:

- migrations
- auth hardening
- audit logging
- observability
- queue or worker integration

Deliverables:

- Alembic migrations
- stronger permission boundaries and operation audit
- structured logs and tracing
- move from SQLite to PostgreSQL when concurrency increases
- keep event dispatch idempotent at the message_id boundary
