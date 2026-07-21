# Dora API

A FastAPI service that returns Aquifer biblical content related to highlighted text in the Bible app.

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: Cloud SQL Postgres via psycopg2
- **Package Management**: uv
- **Env loading**: direnv (`.envrc`)
- **Hosting**: Cloud Run

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
│   └── database/            # Database operations
├── tests/
├── Dockerfile               # Cloud Run image
├── cloudbuild.yaml          # Optional Cloud Build pipeline
├── .envrc.example           # direnv environment template
├── pyproject.toml           # Project dependencies
├── uv.lock                  # Locked dependencies
├── Makefile                 # Common development / deploy commands
└── README.md
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)
- [direnv](https://direnv.net/) (loads `.envrc` into your shell)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) (for deploy)
- Cloud SQL instance: `hackathon-2026-503015:us-central1:dora`

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
| `DATABASE_URL` | Postgres URI (Cloud SQL socket or local proxy) |

**Cloud Run** (Unix socket after attaching the instance):

```text
postgresql://USER:PASSWORD@/DBNAME?host=/cloudsql/PROJECT:REGION:INSTANCE
```

**Local** via [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/connect-auth-proxy):

```bash
# Terminal 1 — proxy
cloud-sql-proxy hackathon-2026-503015:us-central1:dora --port=5432

# .envrc for local
export DATABASE_URL='postgresql://postgres:PASSWORD@127.0.0.1:5432/postgres'
```

Then:

```bash
direnv allow
echo $DATABASE_URL   # should print your URI
```

### 3. Run the API locally

```bash
make run       # http://127.0.0.1:8080
# or with auto-reload on :8000:
make dev
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (dev) or `:8080` (run)

## Make Commands

```bash
make install         # Install dependencies (uv sync)
make env             # Create .envrc from .envrc.example
make db              # Open a psql session to Cloud SQL
make dev             # Dev server with auto-reload
make run             # Run server
make test            # Run tests
make lint            # Ruff check
make format          # Ruff format
make clean           # Remove caches
make deploy-source   # Deploy to Cloud Run (remote build)
make deploy          # Local Docker build + push + deploy
```

### Connect to Cloud SQL

```bash
# one-time ADC setup (required by the proxy gcloud starts)
gcloud auth application-default login

# set DATABASE_PASSWORD in .envrc, then:
direnv allow
make db   # uses DATABASE_PASSWORD if set; otherwise prompts
```

## API Endpoints

### Health Check

```
GET /health
Returns: { "status": "healthy" }
```

## Deploy to Cloud Run

Defaults match this hackathon project:

| Setting | Value |
|---|---|
| Project | `hackathon-2026-503015` |
| Region | `us-central1` |
| Service | `dora-api` |
| Cloud SQL | `hackathon-2026-503015:us-central1:dora` |

### One-time GCP setup

```bash
gcloud config set project hackathon-2026-503015

gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com

# The default compute service account acts as both the Cloud Build SA
# (on newer projects) and the Cloud Run runtime SA. Grant it what it needs:
PROJECT_NUMBER=$(gcloud projects describe hackathon-2026-503015 --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding hackathon-2026-503015 \
  --member="serviceAccount:${COMPUTE_SA}" --role="roles/run.admin"
gcloud projects add-iam-policy-binding hackathon-2026-503015 \
  --member="serviceAccount:${COMPUTE_SA}" --role="roles/iam.serviceAccountUser"
gcloud projects add-iam-policy-binding hackathon-2026-503015 \
  --member="serviceAccount:${COMPUTE_SA}" --role="roles/cloudsql.client"
```

If your project uses the legacy Cloud Build service account (`PROJECT_NUMBER@cloudbuild.gserviceaccount.com`), grant it `roles/run.admin` and `roles/iam.serviceAccountUser` as well.

### Deploy (recommended)

With `DATABASE_URL` loaded in your shell (direnv):

```bash
make deploy-source
```

This builds from the `Dockerfile`, attaches Cloud SQL, and passes `DATABASE_URL` straight through as an env var (via a temp `--env-vars-file`, so the `?host=...` query string parses correctly). Your `DATABASE_URL` should use the socket form:

```text
postgresql://postgres:PASSWORD@/postgres?host=/cloudsql/hackathon-2026-503015:us-central1:dora
```

### Alternative: build image only (Cloud Build)

```bash
gcloud builds submit --config cloudbuild.yaml
# then: make deploy  (or gcloud run deploy with the pushed image)
```

### Verify

```bash
gcloud run services describe dora-api --region=us-central1 --format='value(status.url)'
curl "$(gcloud run services describe dora-api --region=us-central1 --format='value(status.url)')/health"
```
