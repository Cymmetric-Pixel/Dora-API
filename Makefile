.PHONY: help install dev run test clean lint format env

help:
	@echo "Dora API - Available Commands:"
	@echo ""
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Run development server with auto-reload"
	@echo "  make run        - Run production server"
	@echo "  make test       - Run tests"
	@echo "  make test-cov   - Run tests with coverage"
	@echo "  make lint       - Run linters (ruff)"
	@echo "  make format     - Format code (ruff format)"
	@echo "  make clean      - Remove Python cache files"
	@echo "  make env        - Create .envrc from .envrc.example"
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
