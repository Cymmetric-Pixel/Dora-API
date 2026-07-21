.PHONY: help install dev run test clean lint format env db deploy deploy-source

# Cloud Run defaults (override: make deploy PROJECT_ID=... REGION=...)
PROJECT_ID ?= hackathon-2026-503015
REGION ?= us-central1
SERVICE ?= dora-api
AR_REPO ?= dora
CLOUD_SQL ?= hackathon-2026-503015:us-central1:dora
DB_INSTANCE ?= dora
DB_USER ?= postgres
DB_NAME ?= dora
IMAGE ?= $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(AR_REPO)/$(SERVICE)

help:
	@echo "Dora API - Available Commands:"
	@echo ""
	@echo "  make install         - Install dependencies"
	@echo "  make dev             - Run development server with auto-reload"
	@echo "  make run             - Run production server"
	@echo "  make test            - Run tests"
	@echo "  make test-cov        - Run tests with coverage"
	@echo "  make lint            - Run linters (ruff)"
	@echo "  make format          - Format code (ruff format)"
	@echo "  make clean           - Remove Python cache files"
	@echo "  make env             - Create .envrc from .envrc.example"
	@echo "  make db              - Open a psql session to Cloud SQL"
	@echo "  make deploy-source   - Deploy to Cloud Run from source (builds remotely)"
	@echo "  make deploy          - Build locally, push, and deploy to Cloud Run"
	@echo ""

install:
	uv sync

dev:
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

run:
	uv run python -m app.main

test:
	uv run pytest

test-cov:
	uv run pytest --cov=app tests/ --cov-report=term-missing

lint:
	uv run ruff check app/

format:
	uv run ruff format app/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

env:
	@if [ ! -f .envrc ]; then \
		cp .envrc.example .envrc; \
		echo ".envrc created from .envrc.example"; \
		echo "Fill in your secrets, then run: direnv allow"; \
	else \
		echo ".envrc already exists"; \
	fi

# Interactive psql via gcloud (starts Cloud SQL Auth Proxy under the hood).
# Needs ADC once: gcloud auth application-default login
# If DATABASE_PASSWORD is set (e.g. via .envrc), skips the password prompt.
db:
	@if [ -n "$$DATABASE_PASSWORD" ]; then \
		PGPASSWORD="$$DATABASE_PASSWORD" gcloud sql connect $(DB_INSTANCE) \
			--project=$(PROJECT_ID) \
			--user=$(DB_USER) \
			--database=$(DB_NAME); \
	else \
		echo "DATABASE_PASSWORD not set — you will be prompted for the password"; \
		gcloud sql connect $(DB_INSTANCE) \
			--project=$(PROJECT_ID) \
			--user=$(DB_USER) \
			--database=$(DB_NAME); \
	fi

# Write env vars YAML so DATABASE_URL query params (?host=...) don't break gcloud parsing
define write-env-file
	@test -n "$$DATABASE_URL" || (echo "DATABASE_URL must be set (e.g. via direnv)" && exit 1)
	@printf '%s\n' \
		'ENVIRONMENT: production' \
		'LOG_LEVEL: INFO' \
		"DATABASE_URL: \"$$DATABASE_URL\"" \
		> /tmp/dora-api-env.yaml

endef

# Fastest path: Cloud Build builds the Dockerfile and deploys
deploy-source:
	$(write-env-file)
	gcloud run deploy $(SERVICE) \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--source=. \
		--platform=managed \
		--allow-unauthenticated \
		--port=8080 \
		--add-cloudsql-instances=$(CLOUD_SQL) \
		--env-vars-file=/tmp/dora-api-env.yaml
	@rm -f /tmp/dora-api-env.yaml

# Local Docker build → Artifact Registry → Cloud Run
deploy:
	$(write-env-file)
	gcloud artifacts repositories describe $(AR_REPO) \
		--project=$(PROJECT_ID) \
		--location=$(REGION) >/dev/null 2>&1 \
		|| gcloud artifacts repositories create $(AR_REPO) \
			--project=$(PROJECT_ID) \
			--location=$(REGION) \
			--repository-format=docker \
			--description="Dora API images"
	gcloud auth configure-docker $(REGION)-docker.pkg.dev --quiet
	docker build -t $(IMAGE):latest .
	docker push $(IMAGE):latest
	gcloud run deploy $(SERVICE) \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--image=$(IMAGE):latest \
		--platform=managed \
		--allow-unauthenticated \
		--port=8080 \
		--add-cloudsql-instances=$(CLOUD_SQL) \
		--env-vars-file=/tmp/dora-api-env.yaml
	@rm -f /tmp/dora-api-env.yaml
