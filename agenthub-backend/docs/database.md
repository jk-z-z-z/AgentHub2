# Database Design

## Principles

- keep the first version SQLite-friendly
- store messages and events separately
- store events as append-only records
- use `message_id` as the orchestration boundary for event dispatch
- represent DAGs with nodes and parent links instead of a run table
- keep execution state on the node itself

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

Reusable tool registry.

### `mcps`

MCP server registry.

### `messages`

Chat messages shown in the UI.

### `message_events`

Append-only event records attached to one message.

Typical flow:

- `message.created` is written when a message row is created
- dispatcher scans pending events for the same `message_id`
- execution events record tool calls, node execution requests, and runtime traces
- task events record child-agent completion and manager review

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

## Current Query Patterns

- list messages in a group
- load one message with all related events
- list nodes in a group and reconstruct tree order by `parent_node_id`
- inspect node state and assignment

## Migration Guidance

SQLite is still fine for development. Move to PostgreSQL when:

- concurrent writes increase
- event volume grows quickly
- background workers are introduced
- audit and approval queries become organization-wide
