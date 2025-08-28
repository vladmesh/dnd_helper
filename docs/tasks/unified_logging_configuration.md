## Unified logging configuration across services

### Objective
- Provide consistent, structured logging (prefer JSON) across `api` and `bot` with minimal code changes and clear operational controls.

### Scope
- Services: `api`, `bot`.
- No DB changes. Avoid new dependencies if possible; prefer standard library.

### Assumptions
- Python 3.11 is used in both services.
- Current logs are plain `logging`/framework defaults; we can adjust at service startup.
- We can add small modules/files per service if that minimizes cross-service build changes.

### Design Decisions
- Common fields: `timestamp` (UTC ISO-8601), `level`, `service`, `logger`, `message`, `correlation_id` (optional, if available), `extra` (flattened if provided).
- Output: JSON by default; human-readable fallback for local debugging.
- Configuration via env vars:
  - `LOG_LEVEL` (default: `INFO`)
  - `LOG_JSON` (default: `true` → JSON; `false` → human-readable)
  - `LOG_SERVICE_NAME` (default: service-specific hardcoded fallback)
- Placement (minimal changes first):
  - Create a tiny `logging_config.py` module inside each service (`api` and `bot`) with identical content. This avoids Dockerfile/shared layout changes now.
  - Option B (future): extract to a shared package (e.g., `shared_logging`) and include in both images; requires adjusting the `bot` Dockerfile.

### Implementation Plan (Minimal Changes)
1) Add `logging_config.py` in each service
   - Path (API): `api/src/dnd_helper_api/logging_config.py`
   - Path (Bot): `bot/src/dnd_helper_bot/logging_config.py`
   - Provide function `configure_logging(service_name: str, json_enabled: bool, level: str)` that:
     - Clears existing handlers on root and framework loggers (e.g., uvicorn in API) to avoid duplicate logs.
     - Sets formatter:
       - JSON formatter: manually assemble JSON via `json.dumps` inside a custom `logging.Formatter` subclass (standard library only).
       - Human formatter: concise single-line format with ISO timestamps.
     - Normalizes timestamps to UTC ISO-8601.
     - Applies level from env with safe fallback.
     - Adds a filter injecting `service` and optional `correlation_id` from log record’s `extra` or context.

2) Wire up in service entrypoints
   - API: in `api/src/dnd_helper_api/main.py` (early in module import) read env vars and call `configure_logging(service_name="api", ...)` before app creation.
   - Bot: in `bot/src/dnd_helper_bot/main.py` (top of `main()` before building the application) call `configure_logging(service_name="bot", ...)`.

3) Env configuration
   - Add to `docker-compose.yml` for both services:
     - `LOG_LEVEL=INFO`
     - `LOG_JSON=true`
   - Allow overriding via `.env`.

4) Optional correlation id
   - API: generate/request-scope `request_id` using middleware (FastAPI request state or header `X-Request-ID` if present). Log handlers can include it via `extra={"correlation_id": request_id}`.
   - Bot: include `update_id` or user/chat IDs as `correlation_id` when logging update handling; keep optional and minimal.

### Testing Plan
- Manual verification in containers:
  1. Build and restart: `docker compose build && docker compose up -d`.
  2. Exercise API endpoints and bot actions.
  3. Inspect logs: `docker compose logs -n 50 api | cat` and `docker compose logs -n 50 bot | cat`.
  4. Confirm identical JSON structure and presence of `service`, `level`, `timestamp`.
  5. Flip `LOG_JSON=false` via `.env` and restart; verify human-readable format.
  6. Change `LOG_LEVEL=DEBUG` and ensure verbosity increases consistently.

- (If adding request id later) API middleware test: make two requests with fixed `X-Request-ID` and verify it appears in logs.

### Rollout Steps
1. Add `logging_config.py` to both services.
2. Call configurator in `api/main.py` and `bot/main.py`.
3. Add env vars to compose (and `.env`).
4. Rebuild and restart only affected services: `docker compose build api bot && docker compose up -d api bot`.
5. Validate logs formats and toggles.

### Edge Cases
- Duplicate handlers if not clearing pre-existing framework handlers (ensure we replace them once).
- Non-JSON-serializable objects in `extra`: stringify safely.
- Timezones: always UTC; ensure `Z` suffix or `+00:00` in ISO.
- Performance: JSON formatting via stdlib is sufficient; avoid heavy allocs in hot paths.

### Definition of Done
- Both services emit JSON logs with identical fields by default.
- `LOG_LEVEL` and `LOG_JSON` env vars control output consistently.
- Service name present in every log entry.
- Human-readable format available when `LOG_JSON=false`.


