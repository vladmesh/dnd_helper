## DnD Helper — Telegram Bot (Microservices)

A microservices-based Python project: a Telegram bot to assist the Dungeon Master in DnD sessions. The system exposes a small HTTP API with FastAPI and relies on PostgreSQL and Redis.

### Stack
- **Language**: Python 3.11+
- **Bot**: `python-telegram-bot`
- **API**: FastAPI
- **Databases**: PostgreSQL
- **Cache/Queue**: Redis
- **Runtime**: Docker, docker compose v2

### Services (conceptual)
- **api**: FastAPI application exposing HTTP endpoints (e.g., health checks, bot webhooks if needed).
- **bot**: Telegram bot worker using `python-telegram-bot` (long polling or webhook).
- **postgres**: PostgreSQL database for persistent storage.
- **redis**: Redis for caching, rate limiting, or background jobs.

> Note: This repository currently contains documentation and scaffolding files. Application code and compose manifests are expected to be added in subsequent steps.

### Prerequisites
- Docker Desktop or Docker Engine
- docker compose plugin (v2)

### Environment Variables
Create a `.env` file in the project root with at least:

```
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# API
API_PORT=8000

# Postgres
POSTGRES_DB=dnd_helper
POSTGRES_USER=dnd_helper
POSTGRES_PASSWORD=change_me
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

### Quick start
1. Prepare `.env` as above.
2. Start the stack:
   - `docker compose up -d`
3. Check containers:
   - `docker compose ps`
   - `docker compose logs -f api`
   - `docker compose logs -f bot`
4. When implemented, the API health should be available at `http://localhost:8000/health`.

### Search scope examples

API supports choosing search scope for monsters and spells. Default is name-only.

Monsters (raw):

```
curl 'http://localhost:8000/monsters/search/raw?q=wolf&lang=en'
curl 'http://localhost:8000/monsters/search/raw?q=shapechanger&search_scope=name_description&lang=en'
```

Spells (raw):

```
curl 'http://localhost:8000/spells/search/raw?q=fire&lang=en'
curl 'http://localhost:8000/spells/search/raw?q=flammable&search_scope=name_description&lang=en'
```

Bot UI shows a toggle row with current scope and allows switching between modes. The active scope is displayed in prompts and results headers. You can continue typing new queries on the results page; the bot will refresh the same message with updated results.

To stop everything:
```
docker compose down
```

### Notes
- Prefer running everything inside containers.
- Use `docker compose` (not `docker-compose`).
- Documentation is intentionally high-level; concrete implementation (code, migrations, routing) is added incrementally.


.