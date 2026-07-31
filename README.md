# DealBrain

Production-ready backend for the DealBrain AI platform.

## Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.12 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x (async + sync operational adapters) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Containerization | Docker / Docker Compose |

## Architecture

The project follows **clean architecture** with clear layer separation:

```
app/
├── main.py                 # Application factory & lifespan
├── core/                   # Config, logging, DI dependencies
├── api/                    # HTTP layer (routes, endpoints)
│   └── v1/
├── schemas/                # Pydantic request/response DTOs
├── services/               # Application use cases (orchestration)
├── domain/                 # Business entities & port interfaces
│   └── interfaces/         # Abstract contracts (Repository, AIProvider)
└── infrastructure/         # External adapters
    ├── database/           # SQLAlchemy models, sessions, repositories
    ├── persistence/        # Sprint 23 sync persistence helpers / bindings
    └── ai/                 # AI provider implementations
```

**Dependency rule:** outer layers depend on inner layers. Domain has no framework imports.

Architecture lock (Sprints 23–40): [docs/architecture/ARCHITECTURE_LOCK.md](docs/architecture/ARCHITECTURE_LOCK.md).  
Persistence guide: [docs/PERSISTENCE.md](docs/PERSISTENCE.md).  
API standards (Sprint 24): [docs/API_STANDARDS.md](docs/API_STANDARDS.md) · [Sprint 24 contract](docs/architecture/SPRINT_24_API_STABILITY.md).  
Production infrastructure (Sprint 25a): [docs/SPRINT_25A_INFRASTRUCTURE.md](docs/SPRINT_25A_INFRASTRUCTURE.md) · [`infra/`](infra/) · [`.github/workflows/ci.yml`](.github/workflows/ci.yml).  
Immutable image publication (Sprint 25b.1): [docs/SPRINT_25B_IMAGE_PUBLICATION.md](docs/SPRINT_25B_IMAGE_PUBLICATION.md) · [`.github/workflows/build-image.yml`](.github/workflows/build-image.yml).

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker & Docker Compose (optional)

### Local Development

```bash
# Clone and enter the project
cd dealbrain

# Copy environment variables
cp .env.example .env

# Install dependencies
uv sync --extra dev

# Start PostgreSQL (Docker)
docker compose up db -d

# Run migrations
uv run alembic upgrade head

# Start the API (dev defaults keep Sprint 17–21 adapters in-memory)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Health check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

Readiness (includes Sprint 23 persistence components): [http://localhost:8000/ready](http://localhost:8000/ready)

### Docker (full stack)

```bash
cp .env.example .env
docker compose up --build

# Run migrations separately
docker compose --profile migrate up migrate
```

## Testing

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
```

## Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic upgrade head

# Rollback one step
uv run alembic downgrade -1
```

## Environment Variables

See [`.env.example`](.env.example) for all supported variables.

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | `DealBrain` |
| `APP_ENV` | Environment (`development`, `staging`, `production`) | `development` |
| `APP_DEBUG` | Enable debug mode | `false` |
| `APP_PORT` | Server port | `8000` |
| `APP_LOG_LEVEL` | Logging level | `INFO` |
| `DATABASE_URL` | PostgreSQL connection string | — |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |

## Adding Features

1. **Domain** — Define entities and port interfaces in `app/domain/`
2. **Infrastructure** — Implement adapters in `app/infrastructure/`
3. **Services** — Write use-case orchestration in `app/services/`
4. **API** — Expose endpoints in `app/api/v1/endpoints/`
5. **Schemas** — Add Pydantic DTOs in `app/schemas/`

### Future AI Modules

Implement `AIProvider` from `app/domain/interfaces/ai_provider.py` and register
concrete adapters under `app/infrastructure/ai/`.

## License

MIT — see [LICENSE](LICENSE).
