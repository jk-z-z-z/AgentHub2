from __future__ import annotations

import argparse

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.auth_service import ensure_default_admin
from app.services.tool_registry import ensure_builtin_tools_seeded


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize AgentHub DB schema and seed required data.")
    parser.add_argument(
        "--create-schema",
        action="store_true",
        help="Create all tables defined by SQLAlchemy Base metadata (no migrations).",
    )
    parser.add_argument(
        "--seed-default-admin",
        action="store_true",
        help="Ensure default admin user exists (admin@example.com).",
    )
    parser.add_argument(
        "--seed-builtin-tools",
        action="store_true",
        help="Seed/update builtin tools registry into DB.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if not (args.create_schema or args.seed_default_admin or args.seed_builtin_tools):
        raise SystemExit(
            "No action selected. Use one or more of: --create-schema --seed-default-admin --seed-builtin-tools"
        )

    if args.create_schema:
        Base.metadata.create_all(bind=engine)

    if args.seed_default_admin:
        db = SessionLocal()
        try:
            ensure_default_admin(db)
        finally:
            db.close()

    if args.seed_builtin_tools:
        ensure_builtin_tools_seeded()


if __name__ == "__main__":
    main()

