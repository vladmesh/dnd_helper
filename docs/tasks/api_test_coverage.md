## API Endpoint Test Coverage — Implementation Plan

### Goal
Establish meaningful automated tests for the API service endpoints with solid behavior checks (not only 200 OK). Ensure tests run fully in containers.

### Scope
- Service: `api` only.
- Endpoints covered: `monsters`, `spells`, and `users` (list, detail, search where applicable, create/update/delete where already implemented).
- Database: Postgres (test DB via compose), schema managed by Alembic migrations.

### Acceptance Criteria
- Tests exist for:
  - Monsters: list, detail (valid/404), search (hit/miss).
  - Spells: list, detail (valid/404), search (hit/miss).
  - Users: list, detail (valid/404), create/update/delete happy-path.
- If a dice endpoint is later added, include: valid expressions, validation errors, caps.
- Tests run green via containerized workflow.
- Assertions verify payload structure and core fields, not just status codes.

### Test Approach
- Use `pytest` as the runner.
- Use `httpx.AsyncClient` with ASGI transport for async tests against the FastAPI app.
- Manage DB via Alembic migrations for schema parity with production.
- Test data created per test (or per module) using database fixtures; avoid cross-test coupling.

### Test Structure
- Directory: `api/tests/`
- Proposed files:
  - `test_smoke.py` (already present, keep as is for healthcheck)
  - `test_monsters.py`
  - `test_spells.py`
  - `test_users.py`

### Fixtures (pytest)
- `app` fixture: imports `dnd_helper_api.main:app`.
- `async_client` fixture: yields `httpx.AsyncClient` built with `ASGITransport(app=app)`.
- `db_session` fixture: yields `sqlmodel.Session` bound to the service engine; ensure clean state per test module (truncate relevant tables or use transactions).
- `migrated_db` fixture (session-scoped): runs `alembic upgrade head` inside the test container before any tests to ensure schema is present.
  - Minimal alternative (if avoiding Alembic in tests): create tables via `SQLModel.metadata.create_all(engine)` strictly for tests. Prefer Alembic for parity.

### Data Seeding Strategy
- For deterministic tests, create data inline in tests using the `db_session` fixture.
- Keep records minimal (1–3 per test case). Avoid global seeds unless test-specific.

### Test Cases (Outline)
- Monsters (`/monsters`):
  - list: returns empty list on clean DB; returns N items after inserts; verify key fields.
  - detail: 404 on non-existent id; valid monster returns expected fields.
  - search: miss (no matches) → empty list; hit → contains only matching items (case-insensitive `ilike`).
  - CRUD: create returns 201 and ignores client `id`; update modifies fields; delete returns 204.
- Spells (`/spells`):
  - mirror monsters’ tests (list/detail/search/CRUD) aligned to spell fields.
- Users (`/users`):
  - list/detail/CRUD happy-path; 404 on non-existent id.

### Running Tests (Containers Only)
- Full suite (API + Bot) from repo root:
  - `./run_test.sh`
- API only:
  - `cd api && docker compose -f docker_compose_tests.yml build | cat`
  - `docker compose -f docker_compose_tests.yml run --rm api-tests | cat`
  - `docker compose -f docker_compose_tests.yml down -v | cat`

### Minimal Changes Required
- Add the new test files under `api/tests/` with fixtures and cases described above.
- Ensure schema is present before tests:
  - Option A (preferred): extend `api/docker_compose_tests.yml` command to run `alembic upgrade head && pytest -q`.
  - Option B: add a tests-only fixture that calls `SQLModel.metadata.create_all(engine)` before test data setup.
  - Choose one; do not mix both.

### Logging in Tests
- Keep default unified logging; do not assert against log lines.
- Use logs for local troubleshooting only.

### Future (Out of Scope for Now)
- Coverage thresholds and reports.
- Load/performance testing.
- Property-based testing for validators.

### Definition of Done
- New tests implemented and passing via the test compose flow.
- No production code changes beyond what’s necessary for reliable tests (fixtures-only where possible).
- Documentation (this file) committed alongside the tests.


