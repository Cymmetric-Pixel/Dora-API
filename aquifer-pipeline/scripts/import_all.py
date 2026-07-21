"""Pull, process, and import every book of the Bible into Postgres, Genesis to Revelation.

    uv run python scripts/import_all.py                      # all 66 books, download + import
    uv run python scripts/import_all.py --start MAT --stop REV
    uv run python scripts/import_all.py --no-run             # build SQL only, skip the DB load
    uv run python scripts/import_all.py --skip-done          # resume, skipping finished books

Canonical book order comes from reference/versification.json. For each book it runs the three
existing scripts in turn:
    1. pull    scripts/download_sample_data.py  -> data/sample/<CODE>/*.json + manifest.json
    2. process scripts/build_tables.py          -> data/sample/<CODE>/flat/{content,keyword}.jsonl
    3. import  scripts/build_sql.py --run -> upsert into contents / keywords

Failures are per-book and non-fatal: the run continues and prints a summary at the end. A book
that finishes the import writes a data/sample/<CODE>/.done marker; --skip-done skips those.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from run_sql import resolve_dsn

VERSIFICATION = Path("reference/versification.json")


def book_codes() -> list[str]:
    v = json.loads(VERSIFICATION.read_text())
    return [code for code, _ in sorted(v.items(), key=lambda kv: kv[1]["book_number"])]


def select_range(codes: list[str], start: str | None, stop: str | None) -> list[str]:
    lo = codes.index(start) if start else 0
    hi = codes.index(stop) + 1 if stop else len(codes)
    return codes[lo:hi]


def sh(script: str, *script_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, f"scripts/{script}", *script_args],
        capture_output=True,
        text=True,
        check=False,
    )


def jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text().splitlines() if line.strip())


@dataclass
class Result:
    code: str
    status: str
    content: int = 0
    keyword: int = 0
    note: str = ""


def import_book(
    code: str, guides: tuple[str, ...] | None, out_root: Path, run: bool, reprocess: bool
) -> Result:
    book_dir = out_root / code
    guide_args = [a for g in guides for a in ("--guide", g)] if guides else ["--all-guides"]

    if not reprocess:
        pull = sh("download_sample_data.py", "--book", code, "--out", str(book_dir), *guide_args)
        if pull.returncode != 0:
            return Result(code, "pull-failed", note=(pull.stderr or pull.stdout).strip()[-300:])
    if not (book_dir / "manifest.json").exists():
        note = "no local data to reprocess" if reprocess else "download matched nothing"
        return Result(code, "no-resources", note=note)

    proc = sh("build_tables.py", str(book_dir))
    if proc.returncode != 0:
        return Result(code, "process-failed", note=(proc.stderr or proc.stdout).strip()[-300:])

    flat = book_dir / "flat"
    n_content = jsonl_count(flat / "content.jsonl")
    n_keyword = jsonl_count(flat / "keyword.jsonl")

    build_args = [str(book_dir)] + (["--run"] if run else [])
    imp = sh("build_sql.py", *build_args)
    if imp.returncode != 0:
        return Result(code, "import-failed", n_content, n_keyword,
                      (imp.stderr or imp.stdout).strip()[-300:])

    if run:
        (book_dir / ".done").write_text("")
    return Result(code, "imported" if run else "built", n_content, n_keyword)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", help="First book code, inclusive (default GEN)")
    p.add_argument("--stop", help="Last book code, inclusive (default REV)")
    p.add_argument("--guide", action="append", help="Guide id (repeatable; default: all guides)")
    p.add_argument("--out-root", type=Path, default=Path("data/sample"))
    p.add_argument("--no-run", action="store_true", help="Build SQL only, do not load the DB")
    p.add_argument("--skip-done", action="store_true", help="Skip books with a .done marker")
    p.add_argument(
        "--reprocess",
        action="store_true",
        help="Skip the download; rebuild + re-import from already-downloaded data",
    )
    args = p.parse_args()

    run = not args.no_run
    if run:
        load_dotenv()
        if not resolve_dsn():
            print("need DIRECT_URL / DATABASE_URL to import (or pass --no-run)", file=sys.stderr)
            return 1

    guides = tuple(args.guide) if args.guide else None
    books = select_range(book_codes(), args.start, args.stop)

    results: list[Result] = []
    for i, code in enumerate(books, 1):
        if args.skip_done and (args.out_root / code / ".done").exists():
            print(f"[{i}/{len(books)}] {code}: skip (done)")
            results.append(Result(code, "skipped"))
            continue
        print(f"[{i}/{len(books)}] {code}: pull -> process -> {'import' if run else 'build'} ...")
        r = import_book(code, guides, args.out_root, run, args.reprocess)
        results.append(r)
        print(f"    {r.status}: {r.content} content, {r.keyword} keyword"
              + (f" | {r.note}" if r.note else ""))

    print("\n=== summary ===")
    ok = {"imported", "built"}
    total_c = sum(r.content for r in results)
    total_k = sum(r.keyword for r in results)
    for r in results:
        print(f"  {r.code:4} {r.status:15} {r.content:6} content {r.keyword:6} keyword"
              + (f"  {r.note}" if r.note else ""))
    good = sum(r.status in ok for r in results)
    print(f"\n{good}/{len(results)} books ok | {total_c} content rows, {total_k} keyword rows")
    failed = [r.code for r in results if r.status.endswith("-failed")]
    if failed:
        print("failed:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
