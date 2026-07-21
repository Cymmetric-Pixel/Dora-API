"""Emit a self-contained Postgres import script from the two flat tables.

    uv run python scripts/build_sql.py data/sample/1john
    uv run python scripts/build_sql.py data/sample/1john --run

Writes imports/import_<dir>.sql: batched multi-row INSERTs into the existing contents and
keywords tables, idempotent via ON CONFLICT. contents upserts (do update) so re-runs pick up
changed rows; keywords is all-key, so it do-nothing-dedupes on (keyword, content_id). Create
the tables once beforehand (psql "$DIRECT_URL" -f schema.sql). Run it with psql
(psql "$DATABASE_URL" -f <file>), or pass --run to execute it directly (see
scripts/run_sql.py for the connection).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from run_sql import resolve_dsn, run

BATCH = 500
CONTENT_COLS = (
    "content_id", "type", "category", "title", "body", "url",
)


def lit(value: object) -> str:
    if value is None or value == "":
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def upsert_clause(key: tuple[str, ...], cols: tuple[str, ...]) -> str:
    updatable = [c for c in cols if c not in key]
    target = ", ".join(key)
    if not updatable:
        return f"on conflict ({target}) do nothing"
    sets = ",\n    ".join(f"{c} = excluded.{c}" for c in updatable)
    return f"on conflict ({target}) do update set\n    {sets}"


def insert_batches(
    table: str, cols: tuple[str, ...], key: tuple[str, ...], rows: list[dict]
) -> list[str]:
    conflict = upsert_clause(key, cols)
    out = []
    for i in range(0, len(rows), BATCH):
        chunk = rows[i : i + BATCH]
        values = ",\n".join("(" + ", ".join(lit(r.get(c)) for c in cols) + ")" for r in chunk)
        cols_sql = ", ".join(cols)
        out.append(f"insert into {table} ({cols_sql}) values\n{values}\n{conflict};")
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("src", nargs="?", default="data/sample", type=Path)
    p.add_argument(
        "--run", action="store_true", help="Execute the emitted SQL against the database"
    )
    args = p.parse_args()

    src = args.src
    flat = src / "flat"
    content = [json.loads(line) for line in (flat / "content.jsonl").read_text().splitlines()]
    keyword = [json.loads(line) for line in (flat / "keyword.jsonl").read_text().splitlines()]

    kw_cols = ("keyword", "content_id")
    parts = ["begin;"]
    parts += insert_batches("contents", CONTENT_COLS, ("content_id",), content)
    parts += insert_batches("keywords", kw_cols, kw_cols, keyword)
    parts.append("commit;")

    out_dir = Path("imports")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"import_{src.name}.sql"
    out_file.write_text("\n\n".join(parts) + "\n")
    print(f"wrote {out_file}: {len(content)} content + {len(keyword)} keyword rows")

    if args.run:
        load_dotenv()
        dsn = resolve_dsn()
        if not dsn:
            print("--run needs DIRECT_URL / DATABASE_URL in the environment")
            return 1
        run(out_file, dsn)
        print(f"ran {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
