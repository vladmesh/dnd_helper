## Bot Test Coverage — Implementation Plan

### Goal
Introduce automated tests for the Telegram bot covering critical handlers, keyboards, and repository interactions, runnable fully in containers.

### Scope
- Service: `bot` only.
- No real API calls or Telegram network interactions — all external IO mocked.

### Acceptance Criteria
- Tests cover:
  - Dice flow handler (callback patterns: `dice:(d20|d6|2d6|custom)`).
  - Search flow entry via text and menu callbacks for monsters and spells.
  - Main menu navigation (`menu:main`).
  - Pagination helper utilities (deterministic output).
  - API client repository behavior (success/error paths) with mocked HTTP client.
- Tests run green via `bot/docker_compose_tests.yml`.

### Test Approach
- Use `pytest`.
- For handlers: use python-telegram-bot testing utilities (e.g., `ApplicationBuilder().bot = MockBot`) or build/update objects with minimal fakes to call handlers directly.
- For repositories: mock `httpx.AsyncClient`/`httpx.Client` responses.
- For keyboards/utils: pure unit tests over small functions.

### Proposed Test Structure
- Directory: `bot/tests/`
- Files:
  - `test_smoke.py`: simple import/application wiring check (already present).
  - `test_dice.py`: extend with callback query cases, result formatting assertions.
  - `test_search.py`: verify query routing and reply construction for monsters/spells (mock API client).
  - `test_keyboards.py`: verify callback data and pagination keyboard shape.
  - `test_api_client.py`: repository methods happy/error paths with mocked HTTP.

### Fixtures
- `app` fixture: lightweight application with handlers registered (no network).
- `mock_api` fixture: monkeypatch API client in handlers to return deterministic payloads.
- `fake_update` builders: helpers to generate `Update` and `CallbackQuery` for given texts/patterns.

### Running Tests (Containers)
- `cd bot && docker compose -f docker_compose_tests.yml build | cat`
- `docker compose -f docker_compose_tests.yml run --rm bot-tests | cat`
- `docker compose -f docker_compose_tests.yml down -v | cat`

### Minimal Changes Required
- Add missing test files under `bot/tests/` with mocks and helpers.
- Avoid changing bot runtime code; extend tests and small helper fakes only.

### Out of Scope
- End-to-end Telegram API testing.
- Live API service integration tests.

### Definition of Done
- Tests implemented and passing in container.
- No changes to production bot logic beyond testability helpers (if needed).
- Documentation (this file) committed.



