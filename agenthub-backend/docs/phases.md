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
- `api/skills`
- `api/acp_providers`
- `api/agent_profiles`
- `api/agent_instances`
- `services/group_service`
- `services/agent_registry_service`

Deliverables:

- create groups
- create user members and agent members
- create tools, MCPs, skills, and ACP providers
- create agent profiles and bind them to tool or MCP or skill or ACP records
- instantiate agents from profiles
- send and store chat messages through HTTP
- establish the first SQLite persistence layer

## Phase 3: Planning And DAG Editing

Goal: let the orchestrator create and revise plans.

Modules:

- `api/jobs`
- `api/job_edges`
- `api/approvals`
- `services/orchestrator_service`
- future `services/planner_service`

Deliverables:

- create plan nodes and edges
- store assignment suggestions
- support in-place DAG edits with revision tracking
- support assignment approval workflow

## Phase 4: Execution Runtime

Goal: run isolated node sessions through AgentScope and external runners.

Modules:

- `api/runs`
- `api/events`
- `services/agentscope_runtime`
- future `services/external_run_service`
- future `services/event_service`

Deliverables:

- start one external run per node
- store node event stream
- expose polling or SSE APIs for node progress
- support cancel and retry for one node

## Phase 5: Replan And Governance

Goal: support orchestrator-led follow-up decisions and safe replanning.

Modules:

- `services/orchestrator_service`
- `services/approval_service`
- `api/approvals`
- future `api/replans`

Deliverables:

- node can report blockers and missing inputs
- orchestrator can auto-answer low-risk questions
- orchestrator can produce replan patches
- human approval gates important replans

## Phase 6: Production Hardening

Goal: improve reliability and enterprise readiness.

Modules:

- migrations
- auth and RBAC
- audit logging
- observability
- queue or worker integration

Deliverables:

- Alembic migrations
- authentication and organization-level permission controls
- structured logs and tracing
- move from SQLite to PostgreSQL when concurrency increases
