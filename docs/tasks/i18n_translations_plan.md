## i18n/translations rollout plan (RU/EN)

Context
- Goal: move to translation tables for all user-facing content, including enum labels. API and Bot must serve/consume RU and EN.
- Assumption: database is empty; data will be seeded from DTN after changes.
- Principle: iterative, small, testable increments; prefer adding over breaking; keep schema stable.

Non-goals
- We do not aim to support >2 languages immediately; design must allow it without schema changes.
- We do not implement complex MT (machine translation) or admin UI in this scope.

### Iteration 1 — DB groundwork: base translation tables
- Add code enum `Language` with values: `ru`, `en` (Python enum only; used by ORM and API).
- Create tables:
  - `monster_translations` (id, monster_id FK, lang, name, description, created_at, updated_at)
  - `spell_translations` (id, spell_id FK, lang, name, description, created_at, updated_at)
- Constraints and indexes:
  - Unique `(monster_id, lang)` and `(spell_id, lang)`
  - Indexes on `(monster_id)`, `(spell_id)`, `(lang)`, and `(name)`
- Alembic migration only adds new tables, no backfill, no drops.
- Deliverables:
  - New SQLModel classes `MonsterTranslation`, `SpellTranslation` (table=True)
  - Alembic migration: create tables, constraints, indexes

### Iteration 2 — Read path: API can return localized content
- API accepts `lang` query param (`ru|en`), default `ru`.
- GET /monsters, /monsters/{id}, /spells, /spells/{id}:
  - Join translations; choose row by requested `lang` with fallback to the other existing language.
  - Response shape:
    - Return the selected language as primary fields (`name`, `description`).
    - Additionally include `translations: { ru: {name, description}, en: {name, description} }` when available.
- Deliverables:
  - Repository/query adjustments to eager-load translations
  - Response serializers to build fallback and `translations` block
  - Basic tests for fallback logic

### Iteration 3 — Write path: API accepts and stores translations
- POST/PUT for monsters and spells:
  - Extend payload with optional `translations: { ru: {name, description}, en: {name, description} }`.
  - If only scalar `name`/`description` provided, map them into requested `lang` (or default `ru`).
  - Persist into `*_translations` with upsert on `(entity_id, lang)`.
- Seed script `seed_from_dtn.py`:
  - Produce RU/EN translation payloads for names/descriptions when available.
- Deliverables:
  - Pydantic/SQLModel DTOs updated (non-breaking; `translations` optional)
  - Write logic for upsert translations
  - Seed updates and tests

### Iteration 4 — Enum label translations schema
- Add table `enum_translations` to localize enum labels:
  - Columns: `id`, `enum_type` (e.g., `spell_school`, `monster_type`, `monster_size`, `danger_level`, `caster_class`), `enum_value` (the canonical code), `lang`, `label`, `description NULL`, `synonyms NULL JSONB`, `created_at`, `updated_at`
  - Unique `(enum_type, enum_value, lang)`; indexes on `(enum_type, lang)`, `(enum_type, enum_value)`
- Decide storage for enum columns:
  - Option E1 (minimal change): keep DB enums; still translate labels via `enum_translations` by matching textual value.
  - Option E2 (simpler long-term): migrate DB enum columns to `VARCHAR` with validated codes (no DB ENUM types). This simplifies future additions and joins.
- Deliverables:
  - SQLModel for `EnumTranslation` (table=True)
  - Alembic migration for the table and indexes
  - If picking E2: migrations converting enum-typed columns to text for: `Spell.school`, `Spell.classes[]`, `Monster.cr`, and anywhere else enums are used; drop obsolete DB enum types

### Iteration 5 — API response: code + label for enums
- For all enum-coded fields in responses return both the canonical code and the localized label, e.g.:
  - "school": { "code": "evocation", "label": "Эвокация" }
  - Arrays (e.g., classes) return array of objects with `{code,label}`.
- Requests continue to use codes only.
- Deliverables:
  - Helper resolver to batch-fetch enum labels by `(enum_type, enum_value, lang)`
  - Response shaping updated in routers/serializers
  - Tests for RU/EN labels and fallbacks

### Iteration 6 — Localize remaining text fields (monsters)
- Move text arrays/objects into translations (if required by scope): `traits`, `actions`, `reactions`, `legendary_actions`, `spellcasting`.
- Schema: keep these columns in `monster_translations` as JSONB, remove from base table usage.
- Deliverables:
  - Extend `MonsterTranslation` with JSONB fields
  - Read/write logic updated accordingly
  - Seed produces localized variants where available

### Iteration 7 — Bot integration
- Persist user language (if not already) and pass `lang` to API.
- Localize keyboards and inline buttons using `enum_translations`.
- Deliverables:
  - Bot repository updates to request localized labels
  - Tests for user language preference flow

### Iteration 8 — Cleanup and removals
- Remove deprecated localization helpers if any; keep base schemas stable.
- If Option E2 chosen, ensure all enum DB types are fully removed; columns are `VARCHAR` with code validation at application level.
- Deliverables:
  - Alembic migrations to drop obsolete DB enum types (if any)
  - Code cleanup (dead fields/paths)

### Data and seeding plan
- After Iteration 3, seed with RU/EN translations from DTN.
- After Iteration 4/5, populate `enum_translations` with both RU and EN labels for all enum codes.
- Validate via smoke tests: API returns localized content and labels; Bot renders localized UI.

### Operational runbook (per iteration)
- Rebuild/restart containers: `./manage.py restart` (wait ~5s after start)
- Run migrations in API container (non-interactive):
  - Generate (if needed) and apply Alembic migrations
- Run test suite: `./run_test.sh` or service-specific test command
- Verify endpoints manually: `/health`, `/monsters?lang=ru`, `/monsters?lang=en`, `/spells?lang=…`

### Risk log
- Converting DB enums to text (Option E2) changes type constraints; mitigate with application-level validators and tests.
- Fallback behavior must be consistent to avoid mixed-language responses; centralized helper is required. 
