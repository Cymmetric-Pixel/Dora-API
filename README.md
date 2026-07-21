# Dora API

A FastAPI service that returns Aquifer biblical content related to highlighted text in the Bible app.

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: Postgres (Cloud SQL) via psycopg2
- **Package Management**: uv
- **Env loading**: direnv (`.envrc`)
- **Hosting**: Render / Cloud Run

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment variables & settings
│   ├── routes.py            # API route registration
│   ├── models/              # Pydantic models for validation
│   ├── handlers/            # API endpoint handlers
│   └── database/            # Database & storage operations
├── tests/
├── .envrc.example           # direnv environment template
├── pyproject.toml           # Project dependencies
├── uv.lock                  # Locked dependencies
├── render.yaml              # Render Blueprint for deployment
├── Makefile                 # Common development commands
└── README.md
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- [direnv](https://direnv.net/) (loads `.envrc` into your shell)
- A Cloud SQL Postgres instance (or any Postgres URL)

### 1. Clone and install

```bash
git clone <your-repo-url>
cd Dora-API
make install   # or: uv sync
```

### 2. Configure environment variables

```bash
make env       # copies .envrc.example → .envrc
```

Edit `.envrc` and set at least:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Postgres URI (Cloud SQL socket or host:port) |

Cloud Run / attached Cloud SQL instance:

```text
postgresql://USER:PASSWORD@/DBNAME?host=/cloudsql/PROJECT:REGION:INSTANCE
```

Local via [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/connect-auth-proxy) on `127.0.0.1:5432`:

```text
postgresql://USER:PASSWORD@127.0.0.1:5432/DBNAME
```

Then allow direnv to load it:

```bash
direnv allow
```

Confirm the vars are in your shell:

```bash
echo $DATABASE_URL
```

If that prints empty, direnv is not hooking into your shell yet. Add the hook for your shell ([direnv install docs](https://direnv.net/docs/hook.html)), open a new terminal in this directory, and run `direnv allow` again.

### 3. Run the API

```bash
make run       # http://127.0.0.1:8000
# or with auto-reload:
make dev
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Make Commands

```bash
make install    # Install dependencies (uv sync)
make env        # Create .envrc from .envrc.example
make dev        # Dev server with auto-reload
make run        # Run server
make test       # Run tests
make lint       # Ruff check
make format     # Ruff format
make clean      # Remove caches
```

## API Endpoints

### Health Check

```
GET /health
Returns: { "status": "healthy" }
```

## Deploy to Render

Use the included `render.yaml` Blueprint. Set `DATABASE_URL` and other secrets in the Render dashboard (not via `.envrc`). Note: the `/cloudsql/...` socket URI only works when the app runs on GCP with that Cloud SQL instance attached; on Render use a public/private IP or Auth Proxy-compatible host URI instead.
