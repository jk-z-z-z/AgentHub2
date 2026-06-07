# Database Design

## Principles

- keep the first version SQLite-friendly
- store display messages and orchestration events separately
- store events as append-only records
- use `message_id` as the orchestration boundary for event dispatch
- keep editable planning state on `group_task_nodes`
- keep workspace snapshots and sandbox/runtime state in dedicated runtime tables

## Core Tables

### `groups`

Conversation and project container.

### `members`

Group participants.

### `agent_profiles`

Reusable agent templates.

### `agent_instances`

Runtime-configured agents created from profiles.

### `tools`

Reusable builtin tool registry.

### `mcps`

MCP server registry.

### `messages`

Chat messages shown in the UI.

### `message_events`

Append-only event records attached to one message.

Typical flow:

- `message.created` is written when a message row is created
- dispatcher scans pending events for the same `message_id`
- execution-category events record tool calls and runtime traces
- task-category events record node execution requests, completion, and manager review

### `group_task_nodes`

Editable DAG nodes.

Key fields:

- `group_id`
- `parent_node_id`
- `node_key`
- `title`
- `detail`
- `status`
- `assignee_member_id`
- `role_required`

The node row is the durable state source for:

- `pending` / `running` / `completed` / `failed`
- assignee tracking
- retry count through `attempt`

### `workspaces`

One runtime workspace per `project` group.

Key fields:

- `project_id`
- `backend_type`
- `source_path`
- `last_snapshot_id`
- `last_snapshot_digest`
- `last_snapshot_path`

The workspace row tracks the source-of-truth project code root and the latest snapshot metadata.

### `sandbox_runs`

Execution sandbox records for both command jobs and deployment pipelines.

Key fields:

- `workspace_id`
- `sandbox_id`
- `sandbox_image`
- `snapshot_id`
- `working_dir`
- `network_enabled`
- `status`

This table stores the concrete sandbox attempt, captured stdout/stderr, and the working directory that later deployment steps may reuse.

### `execution_jobs`

Project command execution jobs created by `/executions` or `project_command_run`.

Key fields:

- `workspace_id`
- `sandbox_run_id`
- `command`
- `cwd`
- `sandbox_image`
- `network_enabled`
- `status`

The job row is the user-facing record; `result_json` keeps exit code, snapshot metadata, docker command, and effective work directory.

### `deployment_jobs`

Deployment pipeline jobs created by `/deployments` or `project_deploy_run`.

Key fields:

- `workspace_id`
- `sandbox_run_id`
- `image_ref`
- `container_name`
- `dockerfile_path`
- `build_context_path`
- `rollback_image_ref`
- `rollback_status`

The job row stores pipeline inputs plus deployment and rollback results. Pre-build/test commands execute in a sandbox first, then docker build/run happens on the host.

## Current Query Patterns

- list messages in a group
- load one message with all related events
- list nodes in a group and reconstruct tree order by `parent_node_id`
- inspect node state and assignment
- resolve the workspace row for a project group
- inspect the latest snapshot metadata for a workspace
- fetch execution/deployment jobs by id and verify workspace-based access
- inspect sandbox stdout/stderr and result payloads for one runtime attempt

## Migration Guidance

SQLite is still fine for development. Move to PostgreSQL when:

- concurrent writes increase
- event volume grows quickly
- workspace/job history becomes long-lived and query-heavy
- background workers are introduced
- audit and approval queries become organization-wide
