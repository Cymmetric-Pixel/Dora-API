# Dora API

A FastAPI service that returns Aquifer biblical content related to highlighted text in the Bible app. Built on a scaffold with async background job processing, Supabase storage, and status polling.

## Architecture Overview

### Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: Supabase Postgres
- **Storage**: Supabase Storage
- **Background Tasks**: Celery (async job processing)
- **Package Management**: uv

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment variables & settings
│   ├── routes.py            # API route registration
│   ├── models/              # Pydantic models for validation
│   │   └── __init__.py
│   ├── handlers/            # API endpoint handlers (business logic)
│   │   ├── __init__.py
│   │   ├── health.py        # Health check endpoint
│   │   └── jobs.py          # Job CRUD endpoints
│   ├── database/            # Database & storage operations
│   │   └── __init__.py
│   └── workers/             # Celery background tasks
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── factories/           # Test data factories
│   │   └── __init__.py
│   └── integration/         # Integration tests
│       └── __init__.py
├── .env.example             # Environment variable template
├── .python-version          # Python version for local + Render
├── render.yaml              # Render Blueprint (web + worker + Redis)
├── pyproject.toml           # Project dependencies
├── uv.lock                  # Locked dependencies
├── Makefile                 # Common development commands
└── README.md
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Supabase account (for database & storage)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd <repo-name>
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

### Running the Application

#### Development Mode

Start the FastAPI server:
```bash
uv run uvicorn app.main:app --reload
```

Start the Celery worker (in a separate terminal):
```bash
uv run celery -A app.workers.celery_app worker --loglevel=info --concurrency=1
```

Access the API documentation at: `http://localhost:8000/docs`

#### Using Make Commands

```bash
make install    # Install dependencies
make dev        # Run development server
make worker     # Run Celery worker
make test       # Run tests
```

## Deploy to Render

This repo includes a [Render Blueprint](https://render.com/docs/blueprint-spec) in `render.yaml` that provisions:

| Service | Type | Purpose |
|---------|------|---------|
| `dora-api` | Web | FastAPI (`uvicorn`) |
| `dora-api-worker` | Background Worker | Celery PDF processing |
| `dora-api-redis` | Key Value | Celery broker / result backend |

### Steps

1. Push this repo to GitHub/GitLab.
2. In the [Render Dashboard](https://dashboard.render.com) → **Blueprints** → **New Blueprint Instance**.
3. Connect the repository (Render reads `render.yaml`).
4. When prompted, set:
   - `SUPABASE_URL` — your Supabase project URL
   - `SUPABASE_KEY` — service role or anon key (match what the app expects)
   - `AQUIFER_API_KEY` — your Aquifer API key
   - `CORS_ORIGINS` — your Vercel frontend origin(s), comma-separated (e.g. `https://your-app.vercel.app`)
5. Deploy. The API will be at `https://dora-api.onrender.com` (or the URL Render assigns).
6. Confirm `GET /health` returns `{"status":"healthy"}`.

Celery broker URLs are wired automatically from the Redis Key Value instance. Python is pinned to **3.13.5** via `PYTHON_VERSION` and `.python-version`. Builds use `uv sync --frozen --no-dev`.

> **Cost note:** The web service is on the free plan; the worker and Redis use starter plans (required for persistent queues / background workers). Adjust `plan` in `render.yaml` as needed.

## API Endpoints

### Health Check
```
GET /health
Returns: { "status": "healthy" }
```

