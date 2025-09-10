## DnD Helper — API + Telegram Bot

DnD Helper is a project that provides a FastAPI HTTP API and a Telegram bot for browsing and searching DnD 5e monsters and spells with localization (i18n) and enum/UI labels. The system runs with Docker, PostgreSQL, and Redis.

### Tech Stack
- **Language**: Python 3.11+
- **API**: FastAPI (Uvicorn)
- **Bot**: `python-telegram-bot`
- **Database**: PostgreSQL
- **Cache/Queue**: Redis
- **Runtime**: Docker, docker compose v2

### Services
- `api`: FastAPI application exposing HTTP endpoints (monsters, spells, i18n, health).
- `bot`: Telegram bot worker using `python-telegram-bot`.
- `postgres`: PostgreSQL for persistent storage.
- `redis`: Redis for caching and lightweight storage.

See `docs/architecture.md` for details.

### Repository Structure (short)
- `api/` — API service
- `bot/` — Telegram bot service
- `shared_models/` — shared domain models
- `docs/` — documentation

### Prerequisites
- Docker Engine or Docker Desktop
- docker compose (v2)

### Environment
Create a `.env` file in the project root with at least:

```
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Postgres
POSTGRES_DB=dnd_helper
POSTGRES_USER=dnd_helper
POSTGRES_PASSWORD=change_me
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
```

### Quick Start
1. Start/rebuild containers:
   - `python3 manage.py restart`
2. Apply database migrations (inside the API container):
   - `python3 manage.py upgrade`
3. Seed data (monsters, spells, enums, UI):
   - `python3 seed.py --all`
4. Health check: open `http://localhost:8000/health` in a browser.

### Seeding
Seeding expects the following JSON files in the project root:
- `seed_data_enums.json`
- `seed_data_spells.json`
- `seed_data_monsters.json`

Run `python3 seed.py --all` to import monsters and spells via the API and upsert enum and UI translations directly in the database (idempotent).

### Tests
Run all service tests in containers:
- `./run_test.sh`
