from __future__ import annotations

import sqlite3


def _column_exists(cur: sqlite3.Cursor, *, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols


def migrate_sqlite_schema_if_needed(db_url: str) -> None:
    """
    Lightweight migration for dev (SQLite only).

    We avoid introducing Alembic for now and only add missing columns in-place.
    """
    if not str(db_url).startswith("sqlite:///"):
        return
    # sqlite:///./agenthub.db
    path = str(db_url).replace("sqlite:///", "", 1)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        # agent_instances: engine fields
        if not _column_exists(cur, table="agent_instances", column="engine_type"):
            cur.execute("ALTER TABLE agent_instances ADD COLUMN engine_type VARCHAR(40) NOT NULL DEFAULT 'internal_llm'")
        if not _column_exists(cur, table="agent_instances", column="engine_config_json"):
            cur.execute("ALTER TABLE agent_instances ADD COLUMN engine_config_json TEXT NOT NULL DEFAULT '{}'")

        # group_task_events: seq
        if not _column_exists(cur, table="group_task_events", column="seq"):
            cur.execute("ALTER TABLE group_task_events ADD COLUMN seq INTEGER NOT NULL DEFAULT 0")

        # group_task_nodes: result protocol fields
        if not _column_exists(cur, table="group_task_nodes", column="attempt"):
            cur.execute("ALTER TABLE group_task_nodes ADD COLUMN attempt INTEGER NOT NULL DEFAULT 0")
        if not _column_exists(cur, table="group_task_nodes", column="input_json"):
            cur.execute("ALTER TABLE group_task_nodes ADD COLUMN input_json TEXT NOT NULL DEFAULT '{}'")
        if not _column_exists(cur, table="group_task_nodes", column="result_json"):
            cur.execute("ALTER TABLE group_task_nodes ADD COLUMN result_json TEXT NOT NULL DEFAULT '{}'")
        if not _column_exists(cur, table="group_task_nodes", column="error"):
            cur.execute("ALTER TABLE group_task_nodes ADD COLUMN error TEXT NOT NULL DEFAULT ''")
        if not _column_exists(cur, table="group_task_nodes", column="receipt_message_id"):
            cur.execute("ALTER TABLE group_task_nodes ADD COLUMN receipt_message_id INTEGER")
        if not _column_exists(cur, table="group_task_nodes", column="agent_run_id"):
            cur.execute("ALTER TABLE group_task_nodes ADD COLUMN agent_run_id INTEGER")

        # group_task_runs: final summary message
        if not _column_exists(cur, table="group_task_runs", column="final_message_id"):
            cur.execute("ALTER TABLE group_task_runs ADD COLUMN final_message_id INTEGER")

        # agent_profiles: template tool/skill configs
        if not _column_exists(cur, table="agent_profiles", column="tools_json"):
            cur.execute("ALTER TABLE agent_profiles ADD COLUMN tools_json TEXT NOT NULL DEFAULT ''")
        if not _column_exists(cur, table="agent_profiles", column="skills_json"):
            cur.execute("ALTER TABLE agent_profiles ADD COLUMN skills_json TEXT NOT NULL DEFAULT ''")

        # agent_runs / agent_run_events (fresh tables) - created by metadata.create_all()

        conn.commit()
    finally:
        conn.close()
