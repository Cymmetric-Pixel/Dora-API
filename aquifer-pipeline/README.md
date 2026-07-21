# aquifer-pipeline

Offline tooling that pulls [Aquifer](https://aquifer.bible) biblical content, flattens it into
a keyword→content index, and loads it into Postgres. Self-contained and independent of the Dora
API app: it has its own dependencies (psycopg 3, not the app's psycopg2) and is run from this
directory.

## Setup

```bash
cd aquifer-pipeline
uv sync
cp .env.example .env   # then set DATABASE_URL (and optionally DIRECT_URL)
```

`DIRECT_URL` (session-mode DSN) is used by the loader; `AQUIFER_API_KEY` / `AQUIFER_BASE_URL`
fall back to the public web key + `api-bn.aquifer.bible` if unset.

## Pipeline

```bash
# 1. create the tables once
psql "$DIRECT_URL" -f schema.sql

# 2. pull raw resources for a book/guide  -> data/sample/<CODE>/*.json
uv run python scripts/download_sample_data.py --book JHN --all-guides

# 3. flatten to the two tables            -> data/sample/<CODE>/flat/{content,keyword}.jsonl
uv run python scripts/build_tables.py data/sample/JHN

# 4. emit + run the upsert SQL            -> imports/import_JHN.sql
uv run python scripts/build_sql.py data/sample/JHN --run
```

`scripts/import_all.py` chains steps 2-4 across every book (Genesis→Revelation); see its
`--help` for `--start/--stop`, `--skip-done`, and `--reprocess`.

## Tables

- `contents` — one row per resource (PK `content_id`): type, category, title, body, url.
- `keywords` — mention index `(keyword, content_id)`; a keyword is a verse id (`JHN.1.1`) or a
  term. No FK to `contents` by design (books load independently); orphans are checked post-load.

## Tests

```bash
uv run pytest
```

Covers the downloader's pagination/termination and the content-batch 404 split (all offline via
`httpx.MockTransport`).
