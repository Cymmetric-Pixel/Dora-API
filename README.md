# Dora API

A FastAPI service that returns Aquifer biblical content related to highlighted text in the Bible app.

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: Supabase Postgres
- **Storage**: Supabase Storage
- **Package Management**: uv
- **Hosting**: Render

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
├── .env.example             # Environment variable template
├── pyproject.toml           # Project dependencies
├── uv.lock                  # Locked dependencies
├── render.yaml              # Render Blueprint for deployment
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

3. **Create environment file**
   ```bash
   make env
   ```
   Then edit `.env` with your Supabase and Aquifer credentials.

### Running the Application

#### Development Mode

```bash
uv run uvicorn app.main:app --reload
```

Access the API documentation at: `http://localhost:8000/docs`

#### Using Make Commands

```bash
make install    # Install dependencies
make dev        # Run development server
make test       # Run tests
```

## API Endpoints

### Health Check
```
GET /health
Returns: { "status": "healthy" }
```

## Deploy to Render

See the deployment instructions in the project, or use the included `render.yaml` Blueprint.
