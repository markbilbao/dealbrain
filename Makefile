.PHONY: install dev run test lint migrate docker-up docker-down format validate-infra validate-oidc validate-staging-deploy

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

# Sprint 25b.2 targeted checks (OIDC/IAM static tests + infra validate helpers)
validate-oidc:
	uv run pytest tests/unit/test_sprint25b2_oidc_iam.py -q
	bash scripts/validate_infra_25a.sh

# Sprint 25b.3 staging deploy contract + predecessor infra tests
validate-staging-deploy:
	uv run pytest \
		tests/unit/test_sprint25b3_staging_deploy.py \
		tests/unit/test_sprint25a_infrastructure.py \
		tests/unit/test_sprint25b1_image_publication.py \
		tests/unit/test_sprint25b2_oidc_iam.py -q
	bash scripts/validate_infra_25a.sh
	bash -n infra/ec2/user_data/staging.sh
	bash -n scripts/deploy/host/dealbrain-staging-deploy.sh
	bash -n scripts/deploy/host/ghcr-login.sh
	bash -n scripts/deploy/host/verify-staging.sh
