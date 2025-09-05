# Unified Test Plan (API + Bot)

## Context
- i18n is denormalized into `monster_translations`, `spell_translations`, `enum_translations`.
- Base entities `Monster` and `Spell` keep only codes/nums/tech fields; localized text is resolved by `?lang=` and fallback.
- Clients (bot) must consume already-localized fields from wrapped endpoints and must not hardcode labels.

References:
- `docs/architecture.md`
- `docs/tasks/i18n_bot_backend_sync_plan.md`
- `docs/tasks/i18n_denormalization_cleanup_plan.md`

## Goals (target state after completion)
- API:
  - Unit tests for every individual handler with all input variants (happy-path and edge/error cases).
  - Integration tests for end-to-end flows (CRUD lifecycle) for raw and wrapped endpoints.
- Bot:
  - Simulated user interactions (messages and inline button clicks) with the Telegram layer, backend mocked.
  - For each interaction, assert the exact backend requests and the exact user-facing messages/markups produced.
- Pre-commit selective test runner:
  - Only text changes (docs/plans/backlog/jsons) → skip tests.
  - Only bot code changed → run bot tests only.
  - Any API or `shared_models` code changed → run full test suite.
- Backlog: separate e2e environment (dedicated compose) with a script driving the bot as a user.

## Current status
- API: unit-тесты хендлеров Monsters/Spells (create/list/detail/update/delete, валидации входов) — DONE
- API: базовые тесты wrapped-list/detail с i18n и labels для Monsters/Spells — DONE
- API: интеграционные CRUD-флоу (raw и wrapped) — TODO (следующим шагом)
- Bot: интеракционные тесты (сообщения/кнопки) с мокнутым бэком — TODO
- Pre-commit селективный раннер тестов — TODO
- Backlog e2e (отдельный compose, драйвер пользователя) — TODO

## Project topology (relevant parts)
- API handlers: `api/src/dnd_helper_api/routers/`
  - `monsters/`: `endpoints_list.py`, `endpoints_detail.py`, `endpoints_mutations.py`, `endpoints_search.py`, `derived.py`, `translations.py`
  - `spells/`: same structure as monsters
  - `users.py`
- Bot handlers: `bot/src/dnd_helper_bot/handlers/`
  - `menu/` (`start.py`, `menus.py`, `settings.py`, `i18n.py`), `monsters/`, `spells/`, `search.py`, `dice.py`, `text_menu.py`
- Shared enums/models: `shared_models/src/shared_models/`

## Test strategy

### A) API: handler-level unit tests (by router/module)
Organize tests by router file to mirror code structure. Extend, don’t rewrite working tests.

- Monsters
  - `endpoints_list`: pagination, sorting, filters, `?lang=ru|en` localization & fallback, invalid query handling.
  - `endpoints_detail`: by id/slug, 404, localization & fallback.
  - `endpoints_mutations`: create/update/patch/delete with `translations` payload variants; validation errors; idempotent delete.
  - `endpoints_search`: query parsing, empty results, limits.
  - `labeled/wrapped` (per current routers): enum labels present as `{code,label}`; wrapped response shape `{entity,translation,labels}`.
- Spells (same matrix as Monsters; add school/classes labels and any range-related fields if present).
- Users: basic CRUD/auth flows (unaffected by i18n) to keep smoke coverage stable.

Notes:
- Cover negative/fallback cases explicitly: EN missing → RU fallback; RU missing → EN fallback.
- If `include_translations=true` is supported, add tests asserting `translations` block structure; otherwise skip.

### B) API: integration flows (CRUD lifecycles)
For each entity type (Monsters, Spells):
- Raw flow: create → get → update/patch → get → delete → verify 404.
- Wrapped flow: same as raw but via wrapped endpoints; verify `{entity, translation, labels}` shape and label correctness for `ru` and `en`.

### C) Bot: interaction tests with backend mocked

Libraries/tools:
- Use `pytest` + `pytest-asyncio` for async handlers, construct PTB `Update` objects (message and `CallbackQuery`) and feed them into `telegram.ext.Application` in-memory.
- Mock backend HTTP via `respx` (httpx) or monkeypatch `dnd_helper_bot.repositories.api_client.ApiClient` methods to assert request shapes and return canned payloads.

Approach:
- Build a small test helper (internal) to produce updates:
  - `make_message_update(text=..., chat_id=...)`
  - `make_callback_update(data=..., message_text=..., chat_id=...)`
- For each handler path, simulate: incoming command/text/callback → assert:
  - Which repository/API client methods were called (path, params, body).
  - Outgoing bot messages and markups (text content, keyboard layout, callback data) match expectations; no hardcoded UI labels (keys must come from i18n mechanism or API).

Coverage by handler groups:
- `menu/start`: start text, main menu, settings, i18n switch.
- `monsters`: list pagination buttons, filters, open detail, back navigation.
- `spells`: list, filters, detail, back navigation.
- `search`: free-text search request/response, empty result.
- `dice`: deterministic formatting only.
- `text_menu`: render static menus via i18n keys.

Localization:
- For RU/EN test vectors, rely on API-provided localized fields in canned responses; assert that fallback behavior in payload is reflected verbatim in the rendered text (bot does not add extra client-side fallback).

### D) Selective tests in pre-commit (plan)

Intent:
- Implement a local pre-commit hook (or adapt existing CI step) that inspects staged changes and runs the minimal necessary test set.

Rules:
1) Only text files changed → skip tests.
   - Extensions/paths: `**/*.md`, `docs/**`, `docs/tasks/**`, `docs/backlog.md`, `**/*.json` (e.g. `seed_data.json`, `spells.json`).
2) Only bot service changed → run bot tests only.
   - Paths under `bot/**` excluding docs/json.
3) Otherwise (any changes in `api/**` or `shared_models/**`) → run full tests.

Execution (inside containers):
- Bot only: `docker compose exec bot pytest -q | cat`
- API only or full: `docker compose exec api pytest -q | cat` and `docker compose exec bot pytest -q | cat`

Implementation sketch:
- A small script invoked by pre-commit/CI to collect `git diff --name-only --cached` and apply rules above; exit early to skip tests when allowed.
## Step-by-step implementation plan (iterations)

### Iteration 1: Stabilize API unit tests per handler
- Restructure/extend tests under `api/tests/` to mirror routers:
  - Add/extend modules for monsters and spells by endpoint group (list/detail/mutations/search/wrapped/labeled).
  - Add RU/EN localization and fallback assertions to list/detail.
  - Add label assertions for labeled/wrapped endpoints.

### Iteration 2: Add API integration flows
- Add CRUD lifecycle tests for Monsters and Spells (raw and wrapped), including negative 404 checks after deletion.

### Iteration 3: Bot test harness and smoke coverage
- Introduce `pytest-asyncio` scaffolding and Update factories.
- Mock backend via `respx` or repository monkeypatching.
- Cover `menu/start` + basic monsters/spells list interactions and one detail view each.

### Iteration 4: Bot handlers full coverage
- Add tests for filters/pagination, back navigation, search flows, and settings/i18n switching.
- Ensure no hardcoded labels; assert usage of i18n keys/UI translations.

### Iteration 5: Selective test runner for pre-commit/CI
- Add a rule-based runner script and wire it into pre-commit/CI with the exact three rules above.

### Iteration 6: Polish & docs
- Review flakiness, stabilize fixtures, document how to run subsets locally.

## Test data and fixtures
- Keep using `api/tests/conftest.py` cleanup order (translations first, then base entities).
- Use minimal per-test payloads; avoid dependency on global seed data.

## Execution notes
- Run tests strictly inside containers using project tooling.
- After container restarts, wait briefly before requests to services.

## Deliverables
- API: handler-level unit tests + CRUD integration flows for monsters and spells; users smoke kept.
- Bot: interaction tests covering messages and buttons with backend mocked, RU/EN and fallback behavior asserted.
- Pre-commit/CI: selective test execution logic as specified.

## Backlog (not in this iteration)
- Full end-to-end tests with a dedicated compose file that spins up all services and a driver that emulates a Telegram user (e.g., via a userbot/Telethon or similar), asserting chat transcripts for predefined journeys.

## Commands (local/CI, inside containers)
```bash
# API tests
docker compose exec api pytest -q | cat

# Bot tests
docker compose exec bot pytest -q | cat
```
