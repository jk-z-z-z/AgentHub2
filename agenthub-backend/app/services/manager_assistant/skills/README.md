# Manager Assistant Skills

This folder holds "skills" (prompt+schema conventions) for the group manager (Master).

## decision

File: `decision.py`

Goal: decide the next action for the manager conversation loop.

### When to use

Call it for every incoming `@管家` message.

### What it decides

- `CHAT`: answer normally, no DAG generation, no execution.
- `ASK_CLARIFY`: ask domain/business questions before planning (max 6).
- `DRAFT_PLAN`: produce a DAG plan JSON.
- `APPLY_PLAN`: user confirms to persist and execute the current draft plan.

### Important constraints

- Clarify questions must focus on business rules, roles, data sources, workflow.
- Do NOT ask infra questions (DB instance/table name/cron/secrets/retries) unless user explicitly asks for deployment/scheduling.

