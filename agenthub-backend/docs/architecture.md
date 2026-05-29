# Backend Architecture

## Core Direction

This backend is designed for an IM-style multi-agent collaboration platform where:

- each group has one global `Orchestrator`
- each plan is represented as a mutable DAG
- each node is a `Job`
- each `Job` executes in its own isolated external session
- human approval is required for assignment confirmation and important replans

## Module Responsibilities

### `api/`

FastAPI routers and endpoint contracts.

Current slice:

- `health`: service health check

Planned slices:

- `groups`: collaboration container
- `members`: group participants
- `agent_profiles`: reusable agent templates
- `agent_instances`: group-bound agents
- `plans`: DAG container
- `jobs`: node lifecycle
- `events`: node and plan progress stream
- `approvals`: assignment, permission, and replan gates
- `runs`: external execution sessions

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

- `OrchestratorService`: planning, routing, replan decisions
- `AgentScopeRuntime`: node execution runtime boundary
- future `ApprovalService`, `EventService`, `ExternalRunService`

## Execution Model

### Group Scope

- a group contains human members and agent members
- agent members are backed by `AgentInstance`
- agent instances are created from `AgentProfile`

### Plan Scope

- a plan is a DAG with nodes and edges
- the DAG is editable in place from the UI
- the backend still records `revision` for replay and audit

### Job Scope

- each job has one execution owner at a time
- the owner can be a user or an agent member
- if the owner is an agent, execution creates an `ExternalRun`

### Decision Flow

- orchestrator suggests assignment
- human confirms assignment
- node agent runs and streams progress
- node agent can raise blockers or questions
- orchestrator decides whether it can answer directly or requires approval
- orchestrator may propose a replan patch
- human confirms important replans
