"""Execute a .sql file against CloudSQL Postgres directly.

    uv run python scripts/run_sql.py imports/import_2john.sql

Connection string comes from --dsn, else DIRECT_URL, else DATABASE_URL (loaded from .env).
The file is sent verbatim, so its own begin;/commit; controls atomicity.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def resolve_dsn(explicit: str | None = None) -> str | None:
    return explicit or os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL")


def run(sql_file: Path, dsn: str) -> None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql_file.read_text())


def main() -> int:
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("sql_file", type=Path)
    p.add_argument("--dsn", default=None, help="Postgres DSN (default DIRECT_URL / DATABASE_URL)")
    args = p.parse_args()

    dsn = resolve_dsn(args.dsn)
    if not dsn:
        print("need --dsn or DIRECT_URL / DATABASE_URL in the environment", file=sys.stderr)
        return 1
    if not args.sql_file.exists():
        print(f"no such file: {args.sql_file}", file=sys.stderr)
        return 1

    run(args.sql_file, dsn)
    print(f"ran {args.sql_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
