## Backend overview

This document tracks backend-related notes and the immediate backlog. Keep documentation concise and actionable.

### Stack (brief)
- Python 3.11, FastAPI (service: `api`)
- PostgreSQL, Redis
- Alembic for migrations
- Docker Compose for local/dev

### Current API (high level)
- Monsters: `GET /monsters`, `GET /monsters/{id}`, `GET /monsters/search?q=...`
- Spells: `GET /spells`, `GET /spells/{id}`, `GET /spells/search?q=...`

## Backlog

### 1) Search flow should return to main menu (not Bestiary/Spells) [DONE]
- Scope: Bot UX primarily. Backend is already returning search results.
- Goal: After showing search results for monsters/spells, the navigation button should bring user back to Main Menu instead of feature roots.
- Acceptance:
  - Search results keyboard contains a "To main menu" button; pressing it shows the main reply keyboard
  - No backend changes required unless additional metadata is needed (N/A for now)

### 2) Unified logging configuration [DONE]
- Goal: Consistent, structured logs across all services.
- Scope: `api`, `bot`.
- Proposal:
  - Define a shared logging format and fields (service, level, timestamp, message, request_id/correlation_id).
  - Choose output: JSON lines by default; human-readable format for local dev optional.
  - Store a reusable template (e.g., `logging_config.py` or `logging.yaml`) in a shared location and import/use it in each service.
  - Ensure configuration via env vars (level, JSON toggle).
- Acceptance:
  - Both services emit logs with identical structure and fields.
  - Service name is present; timestamps are ISO-8601 UTC.
  - Log level and JSON toggle controllable via environment variables.

### 3) Arbitrary dice roll generation
- Goal: Allow generating arbitrary dice expressions (e.g. `2d6+1`, `d20-2`, `3d8+2d4+5`).
- Proposal (backend): Add endpoint `GET /dice?expr=<expression>` that
  - validates safe expressions in a limited grammar: `(<term> ("+"|"-") <term>)*`, where `<term>` is either `NdM` or integer constant
  - supports `N >= 1`, `M in {2,3,4,6,8,10,12,20,100}`; caps `N` and total terms for safety
  - response payload includes: parsed terms, individual rolls per `NdM`, total, normalized expression
- Acceptance:
  - Given `expr=2d6+1` → returns two d6 rolls, modifier 1, correct total
  - Invalid expr returns `422` with error details

### 4) Test coverage (endpoints at minimum)
- Goal: Solid tests for API routers (smoke + behavior).
- Scope: `api` service.
- Minimum test matrix:
  - Monsters: list, detail (valid/404), search (hit/miss)
  - Spells: list, detail (valid/404), search (hit/miss)
  - If dice endpoint is added: valid expressions, validation errors, caps
- Tooling: `pytest`, `httpx.AsyncClient`, seed fixtures as needed
- Acceptance: CI runs tests green; meaningful assertions beyond 200 OK

### 5) Linters/formatters
- Goal: Consistent style and static checks across services.
- Proposal:
  - Ruff for linting (pyproject-managed), Black for formatting, isort for imports
  - Optional: mypy (incremental adoption), pre-commit hooks
- Acceptance:
  - Commands succeed locally and in CI
  - No outstanding linter violations in `api` (and preferably `bot`)

## Notes
- Keep endpoints minimal and predictable; avoid coupling bot UX to API responses unless necessary.
- For dice: implement a small, safe parser rather than `eval`; add input caps to prevent abuse.


