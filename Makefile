.PHONY: install dev run test lint migrate docker-up docker-down format validate-infra

install:
	uv sync

dev:
	uv sync --dev

run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest

lint:
	uv run python scripts/check_ruff_baseline.py

format:
	uv run ruff format app tests
	uv run ruff check --fix app tests

migrate:
	uv run alembic upgrade head

migration:
	uv run alembic revision --autogenerate -m "$(msg)"

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-migrate:
	docker compose --profile migrate up migrate

validate-infra:
	bash scripts/validate_infra_25a.sh
