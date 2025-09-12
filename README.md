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
- Root/sudo access (the deployment script configures Docker and permissions)

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

### Quick Start (local/dev)
1. Start/rebuild containers:
   - `python3 manage.py restart`
2. Apply database migrations (inside the API container):
   - `python3 manage.py upgrade`
3. Seed data (monsters, spells, enums, UI):
   - `python3 seed.py --all`
4. Health check: open `http://localhost:8000/health` in a browser.

### Production Deployment (one-file interactive script)
Use the interactive script to prepare volumes, install Docker/Compose if missing, set up user permissions, generate `.env` and `docker-compose.yml`, run migrations, and start the stack.

1) Run as root (sudo) from the desired deployment directory:
```
sudo -E bash scripts/deploy.sh
```

2) The script will ask for:
- GHCR owner (org/user)
- Image tag (default `latest`)
- API_PORT (default `8000`)
- Postgres settings (DB, USER, PASSWORD, HOST, PORT)
- Admin settings (enable, token)
- Telegram bot token (optional)

Notes:
- The script backs up existing `.env` and `docker-compose.yml` to `*.bak.<timestamp>` before rewriting.
- Data directories are created under `./data/{postgres,redis,admin_uploads}`.
- Only API is exposed externally; Redis/Postgres/Bot are internal.
- Migrations are applied automatically on startup (`alembic upgrade head`).
- The script grants immediate Docker access to the chosen user (no relogin) via ACL on `/var/run/docker.sock`.

### CI/CD and images (GitHub + GHCR) prerequisites
To use the deployment script with prebuilt images from GitHub Container Registry (GHCR), ensure the repository is configured to publish images:

- Enable GitHub Actions for the repository.
- Ensure the workflow `/.github/workflows/publish_images.yml` is present (it builds and pushes API/Bot images on push to `main`).
- In repository settings, allow the workflow token to publish packages:
  - Settings → Actions → General → Workflow permissions → set to “Read and write permissions”.
  - The workflow already requests `packages: write` (see `permissions` block), so no extra secrets are required for GHCR.
- After pushing to `main`, images will appear at:
  - `ghcr.io/<OWNER>/dnd-helper-api:latest` (and `:<sha>`)
  - `ghcr.io/<OWNER>/dnd-helper-bot:latest` (and `:<sha>`)
- Decide image visibility:
  - Public packages: nothing to configure on the server (anonymous pull ok).
  - Private packages: on the server run `docker login ghcr.io` with a Personal Access Token (PAT) that has `read:packages` before running the deployment script.

### Seeding
Seeding expects the following JSON files in the project root:
- `seed_data_enums.json`
- `seed_data_spells.json`
- `seed_data_monsters.json`

Run `python3 seed.py --all` to import monsters and spells via the API and upsert enum and UI translations directly in the database (idempotent).

### Tests
Run all service tests in containers:
- `./run_test.sh`
