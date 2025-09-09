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

### NEW) Shared DTO strategy between API and Bot [Needs Decision]
- Context: We want strict schema validation on both client (bot) and server (API) while avoiding heavy ORM dependencies in the bot. Today `shared_models` contain SQLModel ORM models that are not ideal as transport contracts.
- Approaches:
  1) Keep SQLModel for ORM. Add Pydantic v2 DTOs in `shared_models/dto/*` (Create/Update/Public/Wrapped). Use `ConfigDict(extra='forbid')` for strictness.
     - API: endpoints accept DTOs; convert to SQLModel via `Model.model_validate(dto)` and `sqlmodel_update`.
     - Bot: import the same DTOs to validate request payloads and parse responses.
     - Pros: strict contracts on both sides; no SQLAlchemy in bot; minimal changes in existing ORM.
     - Cons: two model layers (DTO+ORM), requires discipline.
  2) Use pure SQLAlchemy for ORM and Pydantic DTOs for transport (no SQLModel).
     - Pros: maximal control over ORM; one fewer dependency.
     - Cons: more boilerplate; sizable refactor from current SQLModel.
  3) Reuse SQLModel classes as transport (single model for all).
     - Pros: least duplication.
     - Cons: mixes DB and transport concerns; hard to express Create/Update/Public variants; harder strictness per endpoint; pulls ORM into bot.
- Recommendation: Adopt (1). It preserves current ORM usage and delivers strict validation in bot and API with minimal disruption.
- Next steps:
  - Define DTOs for Monsters and Spells (Create/Update/Public/Wrapped).
  - Migrate API endpoints to accept DTOs; keep responses conforming to Public/Wrapped DTOs.
  - Update bot to use DTOs for request/response validation.
  - Document mapping rules and forbid extra fields in all DTOs.

### 0) Async consistency audit across services (api, bot)
- Goal: Ensure code paths that are expected to be asynchronous are consistently async across both services; avoid blocking calls in async contexts.
- Scope:
  - API: routers, DB access patterns, background tasks, HTTP clients.
  - Bot: handlers, API client usage, network IO.
- Acceptance:
  - No synchronous I/O inside async handlers (network, DB, file) without proper offloading.
  - HTTP and DB libraries used in async-compatible modes where applicable.
  - Identified action items documented if issues found.

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

### 3) Arbitrary dice roll generation [DONE]
- Goal: Allow generating arbitrary dice expressions (e.g. `2d6+1`, `d20-2`, `3d8+2d4+5`).
- Proposal (backend): Add endpoint `GET /dice?expr=<expression>` that
  - validates safe expressions in a limited grammar: `(<term> ("+"|"-") <term>)*`, where `<term>` is either `NdM` or integer constant
  - supports `N >= 1`, `M in {2,3,4,6,8,10,12,20,100}`; caps `N` and total terms for safety
  - response payload includes: parsed terms, individual rolls per `NdM`, total, normalized expression
- Acceptance:
  - Given `expr=2d6+1` → returns two d6 rolls, modifier 1, correct total
  - Invalid expr returns `422` with error details
  - Implemented as a simple bot-only flow (no API endpoint)

### 4) Test coverage (endpoints at minimum) [DONE]
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

### 6) Bot test coverage
- Goal: Automated tests for the Telegram bot covering key handlers and flows.
- Scope: `bot` service.
- Areas:
  - Smoke: app wiring and basic startup invariants
  - Handlers: dice flow, search flow (monsters/spells), main menu callbacks
  - Keyboards: callback data formats and pagination helpers
  - API client repository: basic success/error handling with mocked API
- Tooling: `pytest`, PTB test utilities/mocks, `httpx` mocking
- Acceptance:
  - Tests validate handler behavior (callbacks, messages sent, state changes)
  - No external network calls; API interactions mocked
  - Tests run green via `bot/docker_compose_tests.yml`

## Notes
- Keep endpoints minimal and predictable; avoid coupling bot UX to API responses unless necessary.
- For dice: implement a small, safe parser rather than `eval`; add input caps to prevent abuse.


### 7) Multilingual support (Bot UI) [DONE]
- Goal: Provide RU/EN (and potentially more) language support for bot texts and keyboards.
- Scope: `bot` service (handlers, keyboards, messages). API remains language-agnostic for now.
- Acceptance:
  - Language can be switched (command or settings submenu), and persists per user.
  - All current bot flows render localized texts consistently (menus, lists, details, errors).

### 8) Filter/search fields refinement
- Goal: Align and finalize filterable/searchable fields for Spells and Monsters across API and Bot.
- Scope: `api` review of `/spells` and `/monsters` models and derived fields; `bot` quick filters mapping.
- Acceptance:
  - Agreed field list (documented) with types, value domains, and nullability.
  - Bot quick filters map 1:1 to documented fields or derived ones; gaps identified.

### 9) Source discovery for missing DB fields
- Goal: Identify data sources to populate currently missing attributes (e.g., roles, environments, tags, range normalization).
- Scope: Research and propose ingestion/backfill strategy; do not implement ingestion yet.
- Acceptance:
  - Brief report with candidate sources, license notes, and data coverage.
  - Proposed backfill approach (one-time vs. migrations) and risks.

### 10) Tests for new filtering functionality
- Goal: Cover newly added inline filters and list rendering in Bot; extend API tests if backend filters/pagination are added later.
- Scope: `bot` tests for spells/monsters filters, pagination and state; optional `api` when Iteration 3 backend is implemented.
- Acceptance:
  - Bot tests validate toggles, Apply/Reset, pagination over filtered sets.
  - Tests run green via `bot/docker_compose_tests.yml`.

### 11) Linting pass
- Goal: Ensure clean lint status across updated files.
- Scope: `api`, `bot` as needed after feature changes.
- Acceptance:
  - `python manage.py lint` (ruff) passes without violations.

### 12) Remove IDs from UI display [DONE]
- Goal: Stop showing internal IDs in list item labels and detail views.
- Scope: `bot` list buttons and detail messages for monsters and spells.
- Acceptance:
  - List buttons display names without `(#id)` suffix.
  - Detail views show names and content only; no internal IDs exposed.

### 13) Full-text search for localized content (RU/EN)
- Goal: Add FTS for `monster_translations` and `spell_translations` with per-language indexes.
- Scope: `api` service, PostgreSQL GIN indexes.
- Acceptance:
  - Language-specific search works with `lang` parameter.
  - Indexes exist and are used; performance verified on seed data size.

### 14) More informative error logs (500 details)
- Goal: Improve observability by including request context and exception details when HTTP 5xx errors occur.
- Scope: `api` service primarily; minor alignment in `bot` for upstream error surfaces.
- Proposal:
  - Add FastAPI exception handlers/middleware to log:
    - route, method, status code
    - correlation id (if present), user id (if available)
    - exception type, message, stacktrace
    - request payload size (not body), response time
  - Keep response bodies unchanged; do not leak internals to clients in production.
  - Gate verbose stacktraces behind env flag (e.g., `LOG_INCLUDE_TRACEBACK=true`).
- Acceptance:
  - 500 responses produce structured error logs with route/method and exception info.
  - Toggle controls verbosity via env without code changes.
  - No sensitive data (secrets, raw request bodies) in logs.

### 15) Clean up and squash Alembic migrations
- Goal: Reduce migration noise and speed up setup by squashing and cleaning obsolete revisions.
- Scope: `api` service Alembic history.
- Proposal:
  - Remove redundant/empty or superseded revisions.
  - Create a new baseline squashed revision representing current schema.
  - Preserve production safety: perform only after verifying all environments are at `head`.
- Acceptance:
  - Fresh database can be created with a minimal set of migrations (ideally one baseline + recent changes).
  - CI and local setup times improve; no functional changes to runtime schema.

### 16) Align DB schema and Alembic autogenerate (prevent spurious diffs)
- Goal: Stop Alembic autogenerate from emitting unrelated FK/constraint changes when editing unrelated columns.
- Scope: `api` service models and Alembic env.
- Proposal:
  - Ensure ORM metadata for FKs (ondelete, names) match the actual DB (migrations).
  - Stabilize constraint names (use explicit names) to avoid name-based churn.
  - Add Alembic `include_object`/render options to ignore known-noise changes if intentional.
  - Document policy: which constraints/indexes are managed in migrations only vs ORM.
- Acceptance:
  - Running `alembic revision --autogenerate` after a no-op model change yields only the intended column diffs, no FK churn.
  - FK constraints for `monster_translations` and `spell_translations` no longer flap (drop/create) without intentional change.

### 17) Expand logging structure and context propagation
- Goal: Extend structured logging fields and ensure correlation/context propagation across services.
- Scope:
  - Services: `api`, `bot`.
  - Build on `docs/tasks/unified_logging_configuration.md` without breaking current JSON/human-readable outputs.
- Acceptance:
  - Logs include contextual fields where available: `request_id/correlation_id`, `user_id`/`chat_id` (bot), `route`, `method`, `status_code`, `duration_ms`.
  - Correlation IDs propagate between `api` and `bot` for a single user action.
  - Behavior gated via env flags; defaults remain backward compatible.

### 18) Fix broken filters (Bot and API integration) [DONE]
- Goal: Make existing inline filters reliably affect list/search results for Monsters and Spells.
- Scope:
  - Bot: inline filter state, Apply/Reset behavior, pagination over filtered sets.
  - API: ensure query parameters used by the bot are honored and validated.
- Acceptance:
  - Toggling filters updates results deterministically; Reset restores defaults.
  - Pagination remains consistent when filters are applied.
  - Manual tests green; automated tests added/updated where feasible.

### 19) Seed database with canonical content
- Goal: Provide reproducible seed data for Monsters and Spells for local/dev and tests.
- Scope:
  - Define/curate seed dataset; use `seed.py` or fixtures; run inside containers via `manage.py`.
  - Idempotent execution and clear re-run semantics.
- Acceptance:
  - A single command populates baseline data; re-running does not duplicate rows.
  - Documented counts (approximate) after seeding; basic sanity queries return data.
  - Status: Several dozen monsters are still missing; investigate why they are not loaded.

### 20) Test suite warnings cleanup
- Goal: Run test suites and eliminate runtime/deprecation warnings to keep signal high.
- Scope:
  - Services: `api`, `bot`.
  - Address `pytest` warnings, Python deprecations, and library deprecations; configure filters intentionally when fixing is not viable.
- Acceptance:
  - `pytest` output shows zero warnings locally and in CI for touched modules.
  - No new warnings introduced in subsequent runs (guard via CI settings if available).

### 21) Decompose large files into <= 200-line modules
- Goal: Improve maintainability by splitting overly large modules into focused units.
- Scope:
  - Prioritize `api` routers and `bot` handlers where files exceed 200 lines.
  - Non-functional change only; keep public behavior stable and imports updated.
- Acceptance:
  - No single targeted module remains over ~200 lines, except explicitly justified exceptions list (e.g., generated code).
  - All tests pass; lints/formatters remain green after the split.

### 22) Remove dev/test dependencies from production images
- Goal: Ensure prod containers do not contain pytest and other dev-only packages.
- Scope: `api`, `bot` Dockerfiles and compose flows.
- Proposal:
  - Adjust Poetry installation in Dockerfiles to install only main deps (e.g., `--only main`).
  - Provide separate test images/compose using `--with dev` or dedicated test Dockerfiles.
  - Gate via build args/ENV to keep local DX simple; prod CI uses main-only.
- Acceptance:
  - `docker compose up` for prod profile yields images without pytest (verify by `pip show pytest` absent).
  - Test profiles still run full test suites using test images.

### 23) Fix pre-commit hook (conditional tests)
- Goal: The pre-commit hook must not run the full test suite unconditionally. It should decide whether to skip or run a subset of tests based on changed files.
- Problem: Currently the pre-commit hook runs all tests regardless of what changed.
- Scope: Root-level pre-commit configuration and the hook script that triggers tests.
- Rules:
  - If no code files changed → skip tests entirely.
  - If only Bot code changed and neither Shared Models nor API changed → run only Bot tests.
  - If only API code changed and neither Shared Models nor Bot changed → run only API tests.
  - If Shared Models changed OR both services are affected → run the full test suite.
- Implementation notes:
  - Detect file changes against the staged set (preferred) or against the merge base with the target branch.
  - Treat only code directories as signal (e.g., `api/`, `bot/`, `shared_models/`); ignore docs, configs that do not impact runtime unless they affect tests.
  - Execute tests inside containers using dedicated test compose flows (non-interactive), keeping production containers clean.
  - Ensure a fast path when skipping; print a concise summary of the decision for transparency.
- Acceptance:
  - Given only `bot/` files changed → only Bot tests run.
  - Given only `api/` files changed → only API tests run.
  - Given `shared_models/` changed → full test suite runs.
  - Given only docs changed → tests are skipped.

