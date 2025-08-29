## DB and API Alignment Plan (based on docs/fields.md)

### Principles
- Maintain backward compatibility first; extend, do not break existing API/tests.
- Keep changes minimal per iteration; verify after every small step.
- All commands should run inside containers via `manage.py` and docker compose.
- Documentation is in English; code comments in English; commit messages in English.

### Current Snapshot (high-level)
- `Monster` fields: `title`, `description`, `dangerous_lvl`, `hp`, `ac`, `speed` (+ timestamps).
- `Spell` fields: `title`, `description`, `caster_class`, `distance`, `school` (+ timestamps).
- `User` already OK for this scope.
- Persistence: PostgreSQL via SQLModel/SQLAlchemy; migrations via Alembic (run in `api` container).

---

## Iteration 1 — Schema groundwork (additive DB changes only)
**Status**: Completed
Goal: Add core fields needed by docs/fields.md without removing/renaming existing ones. Prefer JSONB for structured/nested data at this stage. Keep defaults to avoid impacting existing rows.

### Monsters: add columns
- `name` TEXT NULL, indexed (mirror of `title` for specification alignment).
- `type` TEXT NULL.
- `size` TEXT NULL (later may become enum: Tiny/Small/Medium/Large/Huge/Gargantuan).
- `alignment` TEXT NULL.
- `hit_dice` TEXT NULL.
- `speeds` JSONB NULL (keys: walk, fly, swim, climb, burrow), default NULL.
- `cr` NUMERIC NULL (accept both numeric and fractional CR; keep as NUMERIC).
- `xp` INTEGER NULL.
- `proficiency_bonus` INTEGER NULL.
- `abilities` JSONB NULL (keys: str, dex, con, int, wis, cha).
- `saving_throws` JSONB NULL (string->int map).
- `skills` JSONB NULL (string->int map).
- `senses` JSONB NULL (keys: passive_perception, darkvision, blindsight, tremorsense, truesight).
- `languages` TEXT[] NULL.
- `damage_immunities` TEXT[] NULL.
- `damage_resistances` TEXT[] NULL.
- `damage_vulnerabilities` TEXT[] NULL.
- `condition_immunities` TEXT[] NULL.
- `traits` JSONB NULL (array of {name, desc}).
- `actions` JSONB NULL (array of {name, desc}).
- `reactions` JSONB NULL (array of {name, desc}).
- `legendary_actions` JSONB NULL (array of {name, desc}).
- `spellcasting` JSONB NULL (object per spec: ability, dc, attack_bonus, lists of spells).
- `tags` TEXT[] NULL.


### Spells: add columns
- `name` TEXT NULL, indexed (mirror of `title`).
- `level` INTEGER NULL (0..9, constraints later).
- `ritual` BOOLEAN NULL.
- `casting_time` TEXT NULL.
- `range` TEXT NULL (keep `distance` for BC).
- `duration` TEXT NULL.
- `concentration` BOOLEAN NULL.
- `components` JSONB NULL (keys: v, s, m, material_desc).
- `classes` TEXT[] NULL.
- `damage` JSONB NULL (keys: dice, type, scaling_by_slot: map<string,string>).
- `saving_throw` JSONB NULL (keys: ability, effect).
- `area` JSONB NULL (keys: shape, size).
- `conditions` TEXT[] NULL.
- `tags` TEXT[] NULL.

### Execution (DB-only)
1) Update models in `shared_models` (add fields; keep existing fields intact).
2) Generate migration inside container:
   - `python manage.py makemigration -m "iteration1_add_core_fields"`
3) Apply migration:
   - `python manage.py upgrade`
4) Smoke-test API comes up: `python manage.py restart` and wait 5s before requests.

Verification checklist:
- Existing tests pass unchanged.
- Creating/reading existing minimal payloads still works.
- New fields default to `null`/empty without breaking responses.

---

## Iteration 2 — API models and endpoints: accept/return new fields (BC)
Goal: Make API accept and return the newly added fields while preserving current request/response shapes for existing clients/tests.

Changes:
- `Monster` and `Spell` Pydantic/SQLModel schemas now include the new optional fields with sensible defaults (None or empty structures).
- `search` endpoints keep current behavior but search by both `title` and `name` (case-insensitive like now). Do not remove `title` usage yet.
- CRUD endpoints accept payloads containing new fields and persist them as-is.

Execution:
1) Extend routers to map new fields transparently (no validation business logic yet).
2) Add minimal tests that POST new fields and expect them back on GET (keep old tests untouched).
3) `python manage.py restart` and run test suite.

Verification checklist:
- Old tests green; new additive tests green.
- PUT preserves unspecified fields.

---

## Iteration 3 — Filtering and search (basic)
Goal: Implement basic filters described in docs (non-exhaustive), keeping endpoints simple.

Monsters:
- Extend `/monsters/search` to accept optional query params: `type`, `size`, `cr_min`, `cr_max`.
- Filter against columns directly (no JSONB filtering yet other than simple key lookups if needed).

Spells:
- Extend `/spells/search` to accept: `level`, `school`, `class` (from `classes`), optional `damage_type`.

Execution:
1) Add optional query params with defaults and build SQL conditions conditionally.
2) Add tests covering a small matrix of filters.
3) `python manage.py restart` and run tests.

Verification checklist:
- Empty query returns current behavior.
- Combining filters works and is indexed where possible.

---

## Iteration 4 — Data migration and deprecation plan
Goal: Align field names with spec while minimizing impact. Start deprecating legacy fields only after clients are updated.

Steps:
- Backfill data:
  - `name = COALESCE(name, title)` for Monsters/Spells (SQL update migration).
  - `range` can be backfilled from `distance` (e.g., `DISTANCE ft` string) if desired; otherwise leave NULL.
- API responds with `name` alongside `title` for a deprecation window.
- Announce deprecation timeline for `title`, `distance`, `dangerous_lvl`, `speed` in favor of `name`, `range`, `cr`, `speeds`.

Execution:
1) Write a migration to backfill `name` from `title`.
2) Add API response fields `name` (and `range` if backfilled) without removing legacy fields.
3) Update seed data (optionally) to populate new fields.

Verification checklist:
- Existing clients unaffected; new clients can rely on `name`.

---

## Iteration 5 — Validation, enums, and constraints
Goal: Tighten schema gradually once data is present and API is stable.

Planned constraints (as separate migrations after monitoring):
- `Monster.size` -> proper enum; reject invalid values.
- `Spell.level` -> 0..9 check constraint.
- JSON schema-like validation at API layer for nested objects (lightweight Pydantic validators).
- Consider unique index on `(name, type)` for Monsters if duplicates should be avoided (confirm requirements first).

Execution:
1) Introduce new Enums in `shared_models.enums` (e.g., `MonsterSize`).
2) Add validators in model classes for nested JSON shape.
3) Autogenerate migration for enum/constraints.

Verification checklist:
- Tests include negative cases for bad values.

---

## Iteration 6 — Performance and JSONB indexing (optional, usage-driven)
Goal: Add indices where profiling indicates benefits.

Candidates:
- GIN indices on JSONB: `abilities`, `skills`, `senses`, `traits`, `actions` if used in filters.
- Functional indexes: lower(name) for case-insensitive search.

Execution:
1) Add indices via Alembic (explicit op.create_index with `postgresql_using='gin'`).
2) Verify query plans with `EXPLAIN ANALYZE` (in dev).

---

## Rollout and QA Checklist
- Develop iteratively; after each iteration:
  - `python manage.py restart`
  - Wait ~5 seconds before making requests.
  - `python manage.py upgrade` if new migrations were added.
  - Run tests (API and any integration relevant).
- Keep seed data in sync with new fields progressively.
- Document API changes (changelog) and deprecation notices.

## Out of Scope (for now)
- Bot changes (can follow once API stabilizes).
- Advanced full-text search and ranking (consider later if needed).


