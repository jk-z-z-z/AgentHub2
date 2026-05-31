# Database Design

## Design Principles

- keep the first version SQLite-friendly
- model DAG runs and nodes explicitly rather than hiding structure in JSON
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

Runtime-configured agents created by users.

Key fields:

- `creator_user_id`
- `display_name`
- `workspace_root`

### `tools`

Registry of reusable tool definitions.

### `mcps`

Registry of MCP server definitions.

### `agent_profile_tools`

Join table between profiles and tools.

### `agent_profile_mcps`

Join table between profiles and MCP servers.

### `messages`

IM chat messages stored separately from future execution events.

### `group_task_runs`

Top-level DAG container for one orchestrated task.

Key fields:

- `group_id`
- `title`
- `goal`
- `status`

### `group_task_nodes`

DAG nodes.

Key fields:

- `run_id`
- `node_key`
- `title`
- `detail`
- `status`
- `assignee_member_id`
- `role_required`

### `group_task_events`

Append-only event log used for DAG progress and audit.

Key fields:

- `run_id`
- `node_id`
- `event_type`
- `payload_json`

Recommended event families:

- `plan.draft.generated`
- `plan.confirmed`
- `node.assigned`
- `node.exec.started`
- `node.exec.thinking`
- `node.exec.tool_call`
- `node.exec.tool_result`
- `node.exec.stream_chunk`
- `node.exec.finished`

## Early Query Patterns

- list all groups
- list runs in one group
- load one run with nodes and deps
- stream events for one node or one run

## Migration Guidance

SQLite is a good fit for the early prototype, but move to PostgreSQL when:

- concurrent writes increase
- event volume grows quickly
- background workers are introduced
- approval and audit queries become organization-wide
