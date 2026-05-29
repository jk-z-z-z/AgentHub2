# Database Design

## Design Principles

- keep the first version SQLite-friendly
- model plans and jobs explicitly rather than hiding structure in JSON
- store events as append-only records
- allow UI-level in-place DAG editing while preserving backend revision history
- isolate execution at the job level

## Stage 0

This document tracks the staged target design.

## Core Tables

### `groups`

Collaboration container for a team conversation.

Key fields:

- `id`
- `name`
- `description`

### `members`

Participant inside a group.

Key fields:

- `group_id`
- `kind`: `user | agent`
- `display_name`
- `agent_instance_id`: only set when the member is an agent

### `agent_profiles`

Reusable agent templates.

Key fields:

- `name`
- `role`
- `system_prompt`
- `default_model_json`
- `planning_mode`

### `agent_instances`

Runtime-configured agents bound to a group.

Key fields:

- `group_id`
- `profile_id`
- `display_name`
- `api_key_ref`
- `base_url`

### `tools`

Registry of reusable tool definitions.

### `mcps`

Registry of MCP server definitions.

### `skills`

Registry of reusable skill definitions.

### `acp_providers`

Registry of ACP-compatible external providers.

### `agent_profile_tools`

Join table between profiles and tools.

### `agent_profile_mcps`

Join table between profiles and MCP servers.

### `agent_profile_skills`

Join table between profiles and skills.

### `agent_profile_acp_bindings`

Join table between profiles and ACP providers.

### `messages`

IM chat messages stored separately from future execution events.

### `plans`

Top-level DAG container for one orchestrated task.

Key fields:

- `group_id`
- `title`
- `goal`
- `status`
- `revision`

### `jobs`

DAG nodes.

Key fields:

- `plan_id`
- `node_key`
- `title`
- `instructions`
- `status`
- `sort_order`

### `job_edges`

DAG edges.

Key fields:

- `plan_id`
- `from_job_id`
- `to_job_id`
- `condition`

### `job_assignments`

Who should execute a job.

Key fields:

- `job_id`
- `assignee_kind`
- `member_id`
- `rationale`

### `job_reports`

Structured result summary from a node.

Key fields:

- `job_id`
- `summary`
- `blockers_json`
- `assumptions_json`
- `missing_inputs_json`
- `suggested_next_steps_json`

### `external_runs`

One isolated execution session per job.

Key fields:

- `job_id`
- `agent_instance_id`
- `provider_type`
- `external_session_id`
- `workspace_path`
- `status`

### `events`

Append-only event log used for UI progress and audit.

Key fields:

- `run_scope`
- `scope_id`
- `event_type`
- `payload_json`

Recommended event families:

- `plan.created`
- `plan.replanned`
- `assignment.suggested`
- `assignment.approved`
- `job.started`
- `job.progress`
- `job.question`
- `job.waiting`
- `job.completed`
- `job.failed`

### `approvals`

Generic approval gate.

Key fields:

- `kind`
- `scope_id`
- `requested_by`
- `status`
- `prompt`
- `decision_note`

## Early Query Patterns

- list all groups
- list plans in one group
- load one plan with jobs and edges
- load one job and its latest external run
- stream events for one job or one plan
- fetch pending approvals for one group

## Migration Guidance

SQLite is a good fit for the early prototype, but move to PostgreSQL when:

- concurrent writes increase
- event volume grows quickly
- background workers are introduced
- approval and audit queries become organization-wide
