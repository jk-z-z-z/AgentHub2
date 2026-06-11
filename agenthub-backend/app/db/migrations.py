from __future__ import annotations

from sqlalchemy import Engine, text


def _table_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {str(row[1]) for row in rows}


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    ).first()
    return row is not None


def _create_group_task_runs(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS group_task_runs (
                group_id INTEGER NOT NULL,
                creator_member_id INTEGER NOT NULL,
                trigger_message_id INTEGER,
                title VARCHAR(255) NOT NULL,
                goal_text TEXT NOT NULL,
                status VARCHAR(32) NOT NULL,
                id INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(group_id) REFERENCES groups (id),
                FOREIGN KEY(creator_member_id) REFERENCES members (id),
                FOREIGN KEY(trigger_message_id) REFERENCES messages (id)
            )
            """
        )
    )


def _create_group_task_nodes(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS group_task_nodes (
                group_id INTEGER NOT NULL,
                run_id INTEGER NOT NULL,
                parent_node_id INTEGER,
                node_key VARCHAR(80) NOT NULL,
                title VARCHAR(255) NOT NULL,
                detail TEXT NOT NULL,
                role_required VARCHAR(120),
                status VARCHAR(32) NOT NULL,
                assignee_kind VARCHAR(16) NOT NULL,
                assignee_member_id INTEGER,
                attempt INTEGER NOT NULL,
                input_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                error TEXT NOT NULL,
                output_summary TEXT NOT NULL,
                manager_review_status VARCHAR(32) NOT NULL,
                manager_review_note TEXT NOT NULL,
                reviewed_at DATETIME,
                reviewed_by_member_id INTEGER,
                id INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(group_id) REFERENCES groups (id),
                FOREIGN KEY(run_id) REFERENCES group_task_runs (id),
                FOREIGN KEY(parent_node_id) REFERENCES group_task_nodes (id),
                FOREIGN KEY(assignee_member_id) REFERENCES members (id),
                FOREIGN KEY(reviewed_by_member_id) REFERENCES members (id)
            )
            """
        )
    )


def _create_task_indexes(conn) -> None:
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_group_task_runs_group_id ON group_task_runs (group_id)",
        "CREATE INDEX IF NOT EXISTS idx_group_task_runs_status ON group_task_runs (status)",
        "CREATE INDEX IF NOT EXISTS idx_group_task_runs_creator_member_id ON group_task_runs (creator_member_id)",
        "CREATE INDEX IF NOT EXISTS idx_group_task_nodes_group_id ON group_task_nodes (group_id)",
        "CREATE INDEX IF NOT EXISTS idx_group_task_nodes_run_id ON group_task_nodes (run_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_group_task_nodes_run_node_key ON group_task_nodes (run_id, node_key)",
        "CREATE INDEX IF NOT EXISTS idx_group_task_nodes_status ON group_task_nodes (status)",
        "CREATE INDEX IF NOT EXISTS idx_group_task_nodes_assignee_member_id ON group_task_nodes (assignee_member_id)",
        "CREATE INDEX IF NOT EXISTS idx_group_task_nodes_parent_node_id ON group_task_nodes (parent_node_id)",
        "CREATE INDEX IF NOT EXISTS idx_message_events_run_id ON message_events (run_id)",
    ]
    for statement in statements:
        conn.execute(text(statement))


def _ensure_groups_schema(conn) -> None:
    if not _table_exists(conn, "groups"):
        return
    group_columns = _table_columns(conn, "groups")
    if "creator_user_id" not in group_columns:
        conn.execute(text("ALTER TABLE groups ADD COLUMN creator_user_id INTEGER"))
        conn.execute(text("UPDATE groups SET creator_user_id = 1 WHERE creator_user_id IS NULL"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_groups_creator_user_id ON groups (creator_user_id)"))


def _normalize_agent_engine_types(conn) -> None:
    if not _table_exists(conn, "agent_instances"):
        return
    columns = _table_columns(conn, "agent_instances")
    if "engine_type" not in columns:
        return
    conn.execute(
        text(
            """
            UPDATE agent_instances
            SET engine_type = 'agentscope_react'
            WHERE engine_type IS NULL OR TRIM(engine_type) = ''
            """
        )
    )


def run_sqlite_task_schema_migrations(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    desired_run_columns = {
        "id",
        "group_id",
        "creator_member_id",
        "trigger_message_id",
        "title",
        "goal_text",
        "status",
        "created_at",
        "updated_at",
    }
    desired_node_columns = {
        "id",
        "group_id",
        "run_id",
        "parent_node_id",
        "node_key",
        "title",
        "detail",
        "role_required",
        "status",
        "assignee_kind",
        "assignee_member_id",
        "attempt",
        "input_json",
        "result_json",
        "error",
        "output_summary",
        "manager_review_status",
        "manager_review_note",
        "reviewed_at",
        "reviewed_by_member_id",
        "created_at",
        "updated_at",
    }

    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        _ensure_groups_schema(conn)

        run_columns = _table_columns(conn, "group_task_runs") if _table_exists(conn, "group_task_runs") else set()
        rebuild_runs = bool(
            run_columns
            and ("dag_json" in run_columns or "runtime_dir" in run_columns or not desired_run_columns.issubset(run_columns))
        )
        node_columns = _table_columns(conn, "group_task_nodes") if _table_exists(conn, "group_task_nodes") else set()
        rebuild_nodes = bool(node_columns and not desired_node_columns.issubset(node_columns))

        if rebuild_runs:
            conn.execute(text("DROP TABLE IF EXISTS group_task_nodes"))
            conn.execute(text("DROP TABLE IF EXISTS group_task_runs"))
            _create_group_task_runs(conn)
            _create_group_task_nodes(conn)
        elif rebuild_nodes:
            conn.execute(text("DROP TABLE IF EXISTS group_task_nodes"))
            _create_group_task_runs(conn)
            _create_group_task_nodes(conn)
        else:
            _create_group_task_runs(conn)
            _create_group_task_nodes(conn)

        if _table_exists(conn, "message_events") and "run_id" not in _table_columns(conn, "message_events"):
            conn.execute(text("ALTER TABLE message_events ADD COLUMN run_id INTEGER"))
        if rebuild_runs and _table_exists(conn, "message_events") and "run_id" in _table_columns(conn, "message_events"):
            conn.execute(text("UPDATE message_events SET run_id = NULL"))

        _normalize_agent_engine_types(conn)
        _create_task_indexes(conn)
        conn.execute(text("PRAGMA foreign_keys=ON"))
