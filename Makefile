.PHONY: help install dev run test clean lint format env secret deploy deploy-source

# Cloud Run defaults (override: make deploy PROJECT_ID=... REGION=...)
PROJECT_ID ?= hackathon-2026-503015
REGION ?= us-central1
SERVICE ?= dora-api
AR_REPO ?= dora
CLOUD_SQL ?= hackathon-2026-503015:us-central1:dora
SECRET_NAME ?= dora-database-url
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
	@echo "  make secret          - Push DATABASE_URL to Secret Manager"
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

# Store DATABASE_URL in Secret Manager (creates secret or adds a new version)
secret:
	@test -n "$$DATABASE_URL" || (echo "DATABASE_URL must be set (e.g. via direnv)" && exit 1)
	@gcloud secrets describe $(SECRET_NAME) --project=$(PROJECT_ID) >/dev/null 2>&1 \
		&& printf '%s' "$$DATABASE_URL" | gcloud secrets versions add $(SECRET_NAME) \
			--project=$(PROJECT_ID) --data-file=- \
		|| printf '%s' "$$DATABASE_URL" | gcloud secrets create $(SECRET_NAME) \
			--project=$(PROJECT_ID) --replication-policy=automatic --data-file=-

# Fastest path: Cloud Build builds the Dockerfile and deploys
deploy-source: secret
	gcloud run deploy $(SERVICE) \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--source=. \
		--platform=managed \
		--allow-unauthenticated \
		--port=8080 \
		--add-cloudsql-instances=$(CLOUD_SQL) \
		--set-env-vars=ENVIRONMENT=production,LOG_LEVEL=INFO \
		--set-secrets=DATABASE_URL=$(SECRET_NAME):latest

# Local Docker build → Artifact Registry → Cloud Run
deploy: secret
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
		--set-env-vars=ENVIRONMENT=production,LOG_LEVEL=INFO \
		--set-secrets=DATABASE_URL=$(SECRET_NAME):latest
