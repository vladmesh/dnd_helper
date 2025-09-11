## Architecture Overview

This project is a small microservices-based system consisting of two application services and shared infrastructure services. Application services are built with Python 3.11 and packaged with Docker. Dependency management is handled by Poetry.

- API service: FastAPI-based HTTP API
- Bot service: Telegram bot
- Shared infrastructure: PostgreSQL, Redis

## Services

### API Service (`api`)
- Purpose: HTTP API for DnD Helper
- Tech stack: Python 3.11, FastAPI (>=0.110), Uvicorn (>=0.23, standard extras), psycopg (>=3.1, binary), Redis (>=5)
- Entrypoint (compose): `python -m dnd_helper_api.main`
- Port: 8000
- Depends on: `postgres`, `redis`
- Environment: `PYTHONPATH=/app/src`, `.env`
- Compose specifics (this repo): mounts Alembic versions `./api/alembic/versions:/app/alembic/versions`
- Directory (actual):
```
api/
  src/
    dnd_helper_api/
      __init__.py
      main.py
  Dockerfile
  pyproject.toml
  docker_compose_tests.yml
```

### Bot Service (`bot`)
- Purpose: Telegram bot interacting with users and the API
- Tech stack: Python 3.11, python-telegram-bot (>=21), httpx (>=0.27), Redis (>=5)
- Entrypoint (compose): `python -m dnd_helper_bot.main`
- Port: none published by default
- Depends on: `redis`, `postgres`
- Environment: `PYTHONPATH=/app/src`, `.env`
- Directory (actual):
```
bot/
  src/
    dnd_helper_bot/
      __init__.py
      main.py
  Dockerfile
  pyproject.toml
  docker_compose_tests.yml
```

## Shared Infrastructure (defined in top-level compose)
- PostgreSQL: `postgres:16-alpine`, database for persistent storage
- Redis: `redis:7-alpine`, cache, queues, and lightweight storage

## Tooling and Libraries
- Containerization: Docker, docker compose
- Python runtime: 3.11 (slim images)
- Dependency manager: Poetry 1.7.1
- API server: FastAPI, Uvicorn (standard extras)
- Database driver: psycopg (v3, binary)
- Messaging/cache: redis-py
- Bot framework: python-telegram-bot
- HTTP client: httpx
- Testing: pytest
- ORM: SQLModel
- Migrations: Alembic

## Schema and Index Management Policy
- Application schema (tables/columns) is defined via SQLModel models and evolved using Alembic migrations.
- Performance indexes that depend on database-specific features (e.g., PostgreSQL GIN/trgm) are managed exclusively in Alembic migrations and are intentionally not declared in ORM metadata.
- Alembic autogenerate is configured to ignore indexes entirely (managed manually in migrations) to avoid accidental drops/changes.

## Domain Conventions (current)
- Monsters: no `speed` or `speeds` fields; only derived scalar `speed_*` columns (walk/fly/swim/climb/burrow) and `is_flying` flag.
- Spells: no `distance`; use `range` (string). If numeric filters are needed, introduce derived `range_feet` via migration later. Derived `is_concentration` is present and indexed.

## Expected Service Directory Structure (template)
Use this template for any new service to keep structure uniform.
```
service/
  src/
    <python_package>/
      __init__.py
      ...
  tests/
  Dockerfile
  docker_compose_tests.yml
  pyproject.toml
```

## Dockerfile Structure (template)
The Dockerfiles follow a shared pattern. Below is a minimal template derived from the existing service Dockerfiles. Use `EXPOSE 8000` only for HTTP services that publish a port (e.g., the API).
```Dockerfile
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.7.1

# Install dependencies
COPY pyproject.toml /app/pyproject.toml
RUN poetry install --no-interaction --no-ansi --no-root

# Copy source code
COPY src /app/src

# Optional (only for HTTP services that publish a port)
# EXPOSE 8000
```

Notes:
- Keep Poetry virtualenvs disabled inside the container (`POETRY_VIRTUALENVS_CREATE=false`) to install into the system environment.
- `poetry install` is executed before copying the full source to leverage Docker layer caching.

## Top-Level docker compose Service Block (template)
Use this template to add a new application service to the top-level `docker-compose.yml`.
```yaml
services:
  <service_name>:
    build:
      context: ./<service_name>
      dockerfile: Dockerfile
    container_name: <service_name>_container
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app/src
    depends_on:
      - postgres
      - redis
    # Uncomment and adjust if the service exposes a port
    # ports:
    #   - "${<SERVICE_PORT_ENV>:-8080}:8080"
    # Define the service start command
    command: <start_command>
```

Examples:
- API service command: `python -m dnd_helper_api.main`
- Bot service command: `python -m dnd_helper_bot.main`
- In this repository: API build uses `context: .` and `dockerfile: api/Dockerfile`; Bot build uses `context: ./bot` and `dockerfile: Dockerfile`.

## i18n Policy (API)
- Raw endpoints return pristine entities without applied translations.
  - Lists: `GET /monsters/list/raw`, `GET /spells/list/raw`
  - Details: `GET /monsters/{id}`, `GET /spells/{id}`
  - These endpoints set `Content-Language` based on `?lang=` but do not mutate the entity fields.
- Wrapped endpoints carry translations and enum labels alongside the entity.
  - Lists: `GET /monsters/list/wrapped`, `GET /spells/list/wrapped`
  - Details: `GET /monsters/{id}/wrapped`, `GET /spells/{id}/wrapped`
  - Response shape: `{ entity, translation, labels }`.
- Legacy endpoints for collections (e.g., `/spells/wrapped`, `/spells/wrapped-list`, `/monsters/wrapped-list`, `/spells/labeled`, `/monsters/labeled`) are removed. Use the `list/*` and `/{id}/*` endpoints above.
- Client guidance:
  - Bots/UI should consume wrapped endpoints when localized text is required.
  - Admin/testing tools can use raw endpoints for base data without localization.

## Shared Models
- Domain schema lives in `shared_models` and is imported by the API and Alembic.
- Alembic discovers models via imports in `api/alembic/env.py`; migrations are generated from these models and refined manually where needed.

## Logging
- Structured logging with `LOG_LEVEL`, `LOG_JSON`, `LOG_SERVICE_NAME` environment variables.
- API includes middleware that logs unhandled exceptions and 5xx responses with request metadata and timing.

## Health
- API liveness endpoint: `GET /health` → `{ "status": "ok" }`.

## Operations
- Rebuild and start services: `python3 manage.py restart`
- Apply DB migrations inside API container: `python3 manage.py upgrade`

## Seeding
- Seed data via `python3 seed.py --all`.
- Expected files in project root:
  - `seed_data_enums.json`
  - `seed_data_spells.json`
  - `seed_data_monsters.json`
- Behavior:
  - Monsters/Spells are imported via HTTP API (skips if already present).
  - Enum/UI translations are upserted directly inside the API container (idempotent).
