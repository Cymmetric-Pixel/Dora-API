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
uv run celery -A app.workers worker --loglevel=info
```

Access the API documentation at: `http://localhost:8000/docs`

#### Using Make Commands

```bash
make install    # Install dependencies
make dev        # Run development server
make worker     # Run Celery worker
make test       # Run tests
```

## API Endpoints

### Health Check
```
GET /health
Returns: { "status": "healthy" }
```

