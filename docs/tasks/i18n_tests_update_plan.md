# i18n Tests Update Plan (API + Bot)

## Context
- Multilingual text moved to translation tables: `monster_translations`, `spell_translations`, `enum_translations`.
- Base entities `Monster` and `Spell` now hold only numeric/enum/technical fields (`slug`, meta), no localized text.
- API endpoints accept translations via `translations` map and return localized fields by `lang` with fallback.
- Bot must consume already-localized fields from API and avoid any hardcoded labels.

References:
- See `docs/tasks/i18n_denormalization_cleanup_plan.md`
- See `docs/tasks/i18n_bot_backend_sync_plan.md`

## Goals
- Align existing tests with i18n structure (no assumptions about base `name`/`description`).
- Add tests covering `lang`-driven localization and fallback for Monsters/Spells.
- Add tests covering enum label resolution (inline or via labeled endpoints).
- Keep changes minimal: extend, don't rewrite working tests.

## Current Tests Snapshot
- API: `api/tests/`
  - `test_smoke.py`: health OK.
  - `test_users.py`: CRUD, unaffected by i18n.
  - `test_monsters.py`: CRUD + translations in create, list/detail, labeled endpoints.
  - `test_spells.py`: CRUD + translations, extended fields, labeled list/detail.
- Bot: `bot/tests/`
  - `test_smoke.py`: import and application build.
  - `test_dice.py`: utility behavior.

These already partially reflect i18n (passing `translations` on create, lang params, and labeled endpoints).

## Gaps To Address
1. API list/detail endpoints should assert localized `name`/`description` presence in both `ru` and `en` modes with fallback.
2. API responses should optionally include `translations` block when requested (if design includes this; verify and cover).
3. Enum labels coverage consistency for: `Monster.cr`, `Monster.size`, `Monster.type`, `Spell.school`, `Spell.classes` (choose inline `*_label` vs labeled endpoints consistently per routers).
4. Negative cases and fallbacks: when EN missing, RU returned; when RU missing, EN returned.
5. Bot formatting tests for RU/EN inputs: ensure correct usage of `name`/`description` and API-provided labels.

## Step-by-Step Plan

### 1) API: Monsters
- Extend `test_monsters_create_and_list_with_translations`:
  - After create, call `GET /monsters?lang=ru` and `GET /monsters?lang=en` and assert `name` is non-empty and language-appropriate.
  - Add a case where only RU translation is provided; assert EN list/detail fall back to RU.
- Add new test `test_monsters_detail_translations_and_fallback`:
  - Create with `translations` only in EN; fetch RU detail, assert fallback.
- Add new test `test_monsters_enum_labels_consistent`:
  - Use `/monsters/labeled` and `/monsters/{id}/labeled` for RU/EN and assert presence of `{"code","label"}` for enum-coded fields we expose via labeled endpoints.

### 2) API: Spells
- Extend `test_spells_crud_lifecycle`:
  - After create, hit detail with `lang=ru` and `lang=en` and assert `name` resolution and fallback.
- Extend `test_spells_accept_and_return_extended_fields`:
  - Verify labeled endpoints for `school` and `classes` contain `{"code","label"}` in both RU/EN.
- Add new test `test_spells_fallback_behavior`:
  - Create spell with translations only in RU; assert EN list/detail fall back to RU.

### 3) API: Optional `translations` block (if supported)
- If routers support a `include_translations=true` query param:
  - Add `test_monsters_include_translations_block` and `test_spells_include_translations_block` asserting structure:
    - `translations: { ru: {name, description}, en: {name, description} }` with present keys only.
- If not supported, skip this section.

### 4) Bot: Formatting and i18n consumption
- Add tests that mock API payloads (no network):
  - `test_monster_card_format_ru_en`: ensure bot renderer uses `name`, `description`, and label fields correctly for RU and EN.
  - `test_spell_card_format_ru_en`: same for spells.
- Add fallback tests: when EN text missing in payload, renderer outputs RU text returned by API (no client-side extra fallback).
- Ensure no hardcoded labels in code under test. Button captions should be sourced from UI translations mechanism.

### 5) Smoke and integration
- Keep existing smoke tests.
- Optionally add a minimal compose-backed smoke (skipped by default) to hit `/monsters` and `/spells` with `lang` both RU and EN and assert non-empty `name` on at least one entity.

## Test Data and Fixtures
- Continue using `conftest.py` cleaning logic; ensure it deletes translations first, then base entities.
- Use minimal payloads to create entities within tests; avoid reliance on seed data for unit-level tests.

## Execution Notes
- Run tests inside containers only, using project tooling.
- After any migration changes, restart containers and wait briefly before requests.

## Deliverables
- Extended API tests for RU/EN and fallback coverage for monsters and spells.
- New API tests for enum labels consistency.
- New bot unit tests for RU/EN render and fallback.
- Optional tests for `translations` block if supported.

## Out of Scope
- Performance benchmarking.
- Admin UI for translations.

## Commands (for CI/local in containers)
```bash
# API tests
docker compose exec api pytest -q | cat

# Bot tests
docker compose exec bot pytest -q | cat
```
