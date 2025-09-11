## Admin panel and bulk import plan (SQLAdmin + API ops)

### Context and goals
- Replace legacy seeders/parsers usage in ops with a minimal, maintainable admin surface.
- Keep changes small and incremental; do not refactor domain code unless strictly required.
- Reuse small, self-contained pieces from legacy code where it clearly reduces risk.
- Stay within existing architecture: API (FastAPI/SQLModel), Bot, PostgreSQL, Redis. No new microservices unless explicitly justified.
- All commands run inside containers; prefer `manage.py` helpers. Documentation in English.

### Design principles
- Minimal surface: start with read-only admin, then enable curated CRUD where safe.
- Defense-in-depth access control: off by default, token/BASIC auth, optional IP allowlist via envs.
- Bulk imports must be: streaming (low memory), idempotent, resumable (safe to re-run), and auditable.
- Avoid blocking API workers. Use a background worker thread inside the API container with a DB-backed queue. No extra service unless later required.
- Fail fast on missing required data; never silently default required values.

### High-level architecture
- SQLAdmin embedded into API at `/admin`.
- Admin authentication: `ADMIN_ENABLED`, `ADMIN_TOKEN`, optional `ADMIN_BASIC_USER/PASS`. IP allowlist is not planned for now.
- File uploads: API endpoint saves files to a mounted volume; creates a DB row in `admin_jobs` table with status tracking.
- Import worker: long-running background thread in API process polls `admin_jobs` with `status in (queued, running)` and processes tasks using streaming parsing (`ijson`) and existing entity APIs.
- SQLAdmin view for `admin_jobs` to monitor progress and inspect logs/counters.
- Optional later: Streamlit service for rich UI (disabled by default; only if necessary).

---

## Iterations (incremental)

### Iteration 1 — Bootstrap SQLAdmin (read-only) ✅ Done
- Scope:
  - Add SQLAdmin dependency to API and mount `/admin`.
  - Register read-only views for core entities (`Monster`, `Spell`, enum/ui translation tables) using existing SQLModel models in `shared_models`.
  - Gate behind `ADMIN_ENABLED=false` by default; enforce auth via `ADMIN_TOKEN` or HTTP Basic.
- Changes (files):
  - `api/pyproject.toml`: add `sqladmin`.
  - `api/src/dnd_helper_api/main.py`: mount SQLAdmin app; add auth dependency.
  - `docker-compose.yml`: add `ADMIN_*` env vars placeholders (commented), no ports exposure by default.
- Testing:
  - `run_test.sh` passes.
  - Manual: enable admin locally, visit `/admin`, verify lists render, 401/403 without auth.
- Acceptance:
  - Admin disabled by default. When enabled, read-only lists work with auth.

### Iteration 2 — Curated CRUD (safe fields only) ✅ Done
- Scope:
  - Enable create/update for selected models/fields where safe (e.g., translations, enum labels). Keep destructive ops (delete) disabled initially.
  - Add form validators to prevent breaking domain invariants (e.g., no raw i18n mutation that conflicts with wrapped endpoints policy).
- Changes:
  - `api/src/dnd_helper_api/main.py` (or `routers/admin/*.py`): custom SQLAdmin model views with `can_create/can_edit/can_delete` flags and field includes/excludes.
- Testing:
  - CRUD integration tests for allowed models; attempt disallowed ops should be blocked.
- Acceptance:
  - Only curated CRUD is available. Disallowed ops are impossible from UI.

### Iteration 3 — Auth hardening and audit (partially done)
- Scope:
  - Implement token-based auth with optional HTTP Basic; optional IP allowlist from env.
  - Add audit trail: who (subject from header/user), when, what action (entity, id, operation), result.
- Changes:
  - `api/src/dnd_helper_api/logging_config.py`: structured admin logs.
  - `api/src/dnd_helper_api/routers/admin/auth.py`: auth middleware/dependency.
  - Alembic migration + model for `admin_audit` (if we persist audit beyond logs).
- Testing:
  - Auth unit tests; audit writes on admin changes.
- Acceptance:
  - Access strictly controlled; basic audit available in logs and/or DB.

Status:
- Done:
  - Bearer token auth via `ADMIN_TOKEN`.
  - `AdminAudit` model + Alembic migration; DB persistence.
  - SQLAlchemy `after_flush` hook gated to `/admin` requests (actor/path/ip).
- Remaining:
  - Add read-only `AdminAudit` view to SQLAdmin (browse audit records).
  - Optional HTTP Basic (deferred; not needed now).
  - IP allowlist — not planned.

### Iteration 4 — Admin upload endpoint (store only)
- Scope:
  - Add `/admin/upload` (FastAPI form/file) to accept large `.json` files. Store to `/data/admin_uploads` (volume) with metadata row in `admin_jobs` (status=`queued`). No processing yet.
- Changes:
  - `docker-compose.yml`: mount `./data/admin_uploads:/data/admin_uploads` for API.
  - Alembic migration + model: `admin_jobs` with fields: `id`, `job_type` (enum), `args` (jsonb), `file_path`, `status` (queued/running/succeeded/failed), `counters` (jsonb), `error`, `created_at`, `updated_at`, `started_at`, `finished_at`, `launched_by`.
  - `api/src/dnd_helper_api/routers/admin/uploads.py`: endpoint implementation.
- Testing:
  - Upload a large fake JSON (streamed) and verify file saved, DB row created.
- Acceptance:
  - Reliable uploads; job queued in DB; no API worker memory spikes.

### Iteration 5 — Import worker (DB-backed queue, streaming)
- Scope:
  - Background worker thread inside API container reads `admin_jobs` with `job_type in (monsters_import, spells_import)`.
  - Parse JSON via `ijson`, upsert using existing API repo/services, preserve idempotency (detect duplicates by unique keys), measure progress, update `counters` and `status`.
  - Reuse minimal parsing/normalization helpers from legacy code where they are self-contained.
- Changes:
  - `api/src/dnd_helper_api/main.py`: start worker thread on app startup; safe shutdown on exit.
  - `api/src/dnd_helper_api/services/imports.py`: streaming import logic.
  - `api/pyproject.toml`: add `ijson`.
- Testing:
  - Integration test with sample JSON (small) proving streaming path and idempotent re-run.
- Acceptance:
  - Imports run asynchronously; API stays responsive; counters and status reflect progress.

### Iteration 6 — Jobs UI in admin
- Scope:
  - SQLAdmin model view for `admin_jobs` with filters; read-only job detail (counters, error), button to retry/clone job (creates a new queued row).
- Changes:
  - SQLAdmin view config for `AdminJob`.
- Testing:
  - Manually trigger, observe status transitions; retry works.
- Acceptance:
  - Operators can monitor jobs and retry from UI.

### Iteration 7 — Validation, dry-run, and preview
- Scope:
  - Add "dry_run" mode: validate JSON structure, report prospective counts and conflicts without writing.
  - Optional sampling preview (first N items) and schema validation.
- Changes:
  - Extend import service to support `dry_run` flag; update job form to accept it.
- Testing:
  - Dry-run produces report; no DB mutations.
- Acceptance:
  - Safer ops with preview and validation.

### Iteration 8 — Optional Streamlit surface (deferred)
- Scope:
  - If richer UX becomes necessary, add a Streamlit service for dashboards/previews, disabled by default.
- Changes:
-  - `bot` and `api` unchanged; add `streamlit` service block in `docker-compose.yml` following repo template; reuse API endpoints.
- Acceptance:
  - Streamlit provides convenience UI; core ops remain available via API/SQLAdmin.

---

## Data model additions
- `AdminJob` (API ops):
  - `id: UUID`
  - `job_type: enum('monsters_import','spells_import','dry_run')`
  - `args: jsonb` (e.g., entity type, options)
  - `file_path: text`
  - `status: enum('queued','running','succeeded','failed')`
  - `counters: jsonb` (processed, created, updated, skipped, errors)
  - `error: text`
  - `launched_by: text` (operator identifier)
  - timestamps: `created_at`, `updated_at`, `started_at`, `finished_at`

Note: place model in `shared_models` to let Alembic autoload schema; or create an explicit Alembic migration if we prefer not to expose it as a shared domain model. Prefer the former for simplicity and consistency.

## Security model
- Admin disabled by default.
- Access: require `ADMIN_TOKEN` (Bearer) or HTTP Basic with `ADMIN_BASIC_USER/PASS`.
- `ADMIN_IP_ALLOWLIST` check — not planned for now.
- Do not publish `/admin` externally in production; keep behind private network or reverse proxy rules.

## Ops and rollout
- Local/dev:
  - Enable admin: set `ADMIN_ENABLED=true`, `ADMIN_TOKEN=...` in `.env`.
  - Restart: `python3 manage.py restart`.
  - Migrations: `python3 manage.py upgrade`.
  - Tests: `./run_test.sh` (or selective with `scripts/selective_tests.sh`).
- Prod:
  - Add env vars but keep admin disabled until needed.
  - Ensure volume for `/data/admin_uploads` is provisioned and backed up.
  - After deploy, wait 7s before health checks, per project policy.

## Testing strategy
- Unit: auth dependency, job state machine, import parser (streaming). 
- Integration: admin auth (401/403), CRUD guarded fields, upload flow, small import end-to-end.
- Non-functional: memory usage on large files (ensure streaming), API responsiveness during imports.

## Risks and mitigations
- Blocking API during import → background thread + streaming + periodic yielding; keep heavy CPU work minimal.
- Data corruption on partial failures → idempotent upserts, transaction scopes per item/batch, counters and error capture.
- Leaking admin externally → disabled by default, explicit env gating, ingress rules.
- Schema drift for jobs → centralized model in `shared_models` with Alembic migration.

## Out of scope (for now)
- Full RBAC/SSO, granular permissions.
- Complex dashboards and visual analytics (deferred to Streamlit iteration if needed).
- Separate queue/broker services (RQ/Celery). We keep a DB-backed queue first.

## Env variables (tentative)
- `ADMIN_ENABLED` (bool, default false)
- `ADMIN_TOKEN` (string)
- `ADMIN_BASIC_USER` / `ADMIN_BASIC_PASS` (strings, optional)
- `ADMIN_IP_ALLOWLIST` (comma-separated CIDRs, optional)
- `ADMIN_UPLOAD_DIR` (default `/data/admin_uploads`)

## Endpoints (tentative)
- `GET /admin` — SQLAdmin UI (protected)
- `POST /admin/upload` — upload JSON file (protected)
- `GET /admin/jobs` — SQLAdmin view (protected)

## Acceptance checklist (per iteration)
- Admin disabled by default; enabling is explicit via env.
- Tests pass with `run_test.sh`.
- No broken public API contracts.
- Minimal, targeted changes aligned with existing structure and style.


