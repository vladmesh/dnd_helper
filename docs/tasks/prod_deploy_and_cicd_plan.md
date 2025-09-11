## Production Deployment and CI/CD Plan

### Goal
- Keep production server code-free: only a dedicated compose file, `.env`, seed JSON files, and a seeding script.
- Configure CI/CD so that every push to `main` builds and updates images on the server automatically.

### Assumptions
- Existing services: `api`, `bot`, `postgres`, `redis` (see `docs/architecture.md`).
- Images are built using the existing `api/Dockerfile` and `bot/Dockerfile`.
- Seed CLI exists at `seeding/cli.py`, expects JSON files in project root and API reachability for monsters/spells.

---

## Iteration 1 — Minimal production deployment (no code on server)

### Deliverables
- `docker-compose.prod.yml` stored on the server only (not part of the repo), referencing prebuilt images.
- `.env` file on the server with prod secrets.
- Seed JSON files on the server: `seed_data_enums.json`, `seed_data_spells.json`, `seed_data_monsters.json`.
- Seeding script on the server that runs inside containers and is idempotent.

### Steps
1) Build and push images from CI
- Create CI job that, on push to `main`, builds multi-arch (or amd64) images and pushes them to a registry:
  - `REGISTRY/PROJECT/api:latest` and `REGISTRY/PROJECT/api:<git-sha>`
  - `REGISTRY/PROJECT/bot:latest` and `REGISTRY/PROJECT/bot:<git-sha>`
- Build context and Dockerfiles:
  - API: context `.` dockerfile `api/Dockerfile`
  - Bot: context `bot/` dockerfile `bot/Dockerfile`
- Use Poetry without dev deps in prod images (follow-up task exists in backlog).

2) Prepare server directory (one-time)
- Create directory, e.g. `/opt/dnd-helper`.
- Place on the server (only these files):
  - `docker-compose.prod.yml` (see template below)
  - `.env` with secrets and required variables
  - `seed_data_enums.json`, `seed_data_spells.json`, `seed_data_monsters.json`
  - `seed.sh` (wrapper to seed using running containers)
- Ensure docker compose v2 is installed on the server and the service account can run Docker.

3) Compose file (server-side only)
- Use images from the registry, no bind mounts of code.
- Apply restart policy `unless-stopped`.
- Run API via `python -m dnd_helper_api.main`, Bot via `python -m dnd_helper_bot.main`.
- Expose API port 8000 as needed via env `API_PORT`.

4) Migrations
- After pulling new images and before seeding, run Alembic migrations inside the API container:
  - `docker compose up -d postgres redis`
  - `docker compose up -d api`
  - `docker compose exec -T api alembic upgrade head`

5) Seeding
- With API healthy, seed monsters/spells via HTTP and enums/UI directly in DB through the API container Python process:
  - `docker compose exec -T api python -c "import time; time.sleep(5)"` (grace delay)
  - `docker compose exec -T api curl -sf localhost:8000/health`
  - `docker compose exec -T api python - <<'PY'
from seeding.cli import main as seed_main
import sys
sys.exit(seed_main(["--api-base-url","http://localhost:8000","--all"]))
PY`
- Alternatively, copy a tiny `seed.py` into the image in future, but for now prefer calling module path inside the container if present. If the module is not present in prod image, use a containerized helper image (see Iteration 2).

6) Bot
- Start bot after API migrations are applied:
  - `docker compose up -d bot`

7) Rollback
- Keep `:latest` and specific `:<git-sha>` tags. For rollback:
  - Update compose to point to previous tag; `docker compose pull && docker compose up -d`.

### Template: docker-compose.prod.yml (server-side)
```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  api:
    image: ${REGISTRY}/dnd-helper/api:${API_TAG:-latest}
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app/src
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_JSON=${LOG_JSON:-true}
      - LOG_SERVICE_NAME=api
    depends_on:
      - postgres
      - redis
    ports:
      - "${API_PORT:-8000}:8000"
    command: python -m dnd_helper_api.main

  bot:
    image: ${REGISTRY}/dnd-helper/bot:${BOT_TAG:-latest}
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app/src
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - LOG_JSON=${LOG_JSON:-true}
      - LOG_SERVICE_NAME=bot
    depends_on:
      - redis
      - postgres
    command: python -m dnd_helper_bot.main

volumes:
  postgres_data:
  redis_data:
```

### `.env` (server-side minimal)
- TELEGRAM_BOT_TOKEN=...
- POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
- POSTGRES_HOST=postgres, POSTGRES_PORT=5432
- REDIS_URL=redis://redis:6379/0
- API_PORT=8000
- REGISTRY, API_TAG, BOT_TAG (optional for pinning exact versions)

---

## Iteration 2 — CI/CD wiring

### Deliverables
- CI workflow that builds and pushes images on every push to `main`.
- Server auto-update pipeline: pull new images and restart services when new `latest` (or a new tag) appears.

### Steps
1) CI (example: GitHub Actions)
- Two jobs (can share a matrix): build/push API and Bot.
- Log in to registry (`docker login`), build with cache, tag with `latest` and `git-sha`, push.
- Artifacts: pushed images `REGISTRY/dnd-helper/api`, `REGISTRY/dnd-helper/bot`.

2) Server auto-deploy
- Option A (pull-based): a systemd timer or cron on server runs:
  - `docker compose pull`
  - `docker compose up -d`
  - `docker compose exec -T api alembic upgrade head`
  - optional: seeding idempotent script (can be disabled later when admin replaces it)
- Option B (push-based): CI connects via SSH and runs the same commands remotely.

3) Health checks and gating
- After `up -d`, wait 7 seconds and hit `http://localhost:8000/health`.
- Abort/update alert if health fails.

4) Access logs/monitoring (basic)
- Ensure logs go to stdout and are aggregated by Docker/host.

---

## Iteration 3 — Hardening and housekeeping

- Remove dev/test deps from prod images (Ruff/pytest) — see `docs/backlog.md` item 22.
- Add image labels and build metadata.
- Configure resource limits in compose (CPU/memory) if needed.
- Strict `.env` validation at startup; fail fast on missing required variables.

---

## Iteration 4 — Future changes (backlog)

- Replace seeding flows with an admin UI to manage content in production.
- Add mandatory end-to-end tests executed in CI/CD before deploy; gate deploy on green.
- Optionally move seed JSONs to object storage and fetch in a dedicated one-shot init container.
