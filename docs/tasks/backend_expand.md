## Schema Alignment Roadmap

This roadmap aligns the current models and API with the recommendations in `shared_models/schema_recomendations.md`. Changes are iterative, additive-first, and tested at every step. All commands run in containers via `manage.py` and docker compose.

### Principles
- Extend, don’t break: keep legacy fields for backward compatibility until a deprecation phase.
- Smallest possible edits per iteration; verify after each step.
- Documentation in English; commit messages in English; code comments in English.
- Use `python manage.py restart` for rebuilds/restarts; generate/apply Alembic migrations inside the `api` container.
- Run tests via `./run_test.sh` (both services).

---

## Current Snapshot (baseline)
- Models:
  - `shared_models.Monster`: legacy `speed` and JSONB `speeds` removed; keep only derived `speed_*` columns and flags (e.g., `is_flying`).
  - `shared_models.Spell`: legacy `distance` removed; use normalized `range` (string) for display and consider derived `range_feet` later if needed.
- API:
  - CRUD and very basic search (`name ilike`) for both `monsters` and `spells`.
- Tooling:
  - Migrations: Alembic inside `api` container via `manage.py`.
  - Tests: `./run_test.sh` runs containerized tests for API and Bot.

---

## Iteration 0 — Enums and groundwork (Done)
Goal: Define core enumerations required for filtering/validation; wire them into models for typing/validation without altering storage. No DB migrations.

Scope (enums to add in `shared_models.enums`):
- MovementMode: WALK, FLY, SWIM, CLIMB, BURROW
- SpellComponent: V, S, M
- Environment: ARCTIC, DESERT, FOREST, GRASSLAND, MOUNTAIN, SWAMP, COAST, UNDERDARK, URBAN, PLANAR
- MonsterSize: TINY, SMALL, MEDIUM, LARGE, HUGE, GARGANTUAN
- MonsterType: ABERRATION, BEAST, CELESTIAL, CONSTRUCT, DRAGON, ELEMENTAL, FEY, FIEND, GIANT, HUMANOID, MONSTROSITY, OOZE, PLANT, UNDEAD
- Ability: STR, DEX, CON, INT, WIS, CHA
- DamageType: ACID, COLD, FIRE, FORCE, LIGHTNING, NECROTIC, POISON, PSYCHIC, RADIANT, THUNDER, BLUDGEONING, PIERCING, SLASHING
- Condition: BLINDED, CHARMED, DEAFENED, FRIGHTENED, GRAPPLED, INCAPACITATED, INVISIBLE, PARALYZED, PETRIFIED, POISONED, PRONE, RESTRAINED, STUNNED, UNCONSCIOUS, EXHAUSTION
- Targeting: SELF, CREATURE, CREATURES, OBJECT, POINT
- AreaShape: LINE, CONE, CUBE, SPHERE, CYLINDER
- CastingTimeNormalized: ACTION, BONUS_ACTION, REACTION, MINUTE_1, MINUTE_10, HOUR_1, HOUR_8
- SaveEffect: HALF, NEGATE, PARTIAL
- MonsterRole: BRUTE, SKIRMISHER, ARTILLERY, CONTROLLER, LURKER, SUPPORT, SOLO

Execution:
- Add enums to `shared_models/enums.py`.
- Optionally reference them in `shared_models` models for type hints/validation only; keep DB columns as TEXT/ARRAY for now to avoid migrations.
- No API behavior change; docs only. Run tests to ensure imports/serialization are intact.

Acceptance:
- Project builds; tests remain green; no schema changes.

---

## Iteration 1 — Monsters: additive fields (no removals) (Done)
Goal: Add recommended monster fields and derived columns as nullable. Keep `speed` intact. No population logic yet.

DB/model changes (add columns; all nullable, indexed where useful):
- Localization: `name_ru TEXT`, `name_en TEXT`, `slug TEXT`
- Taxonomy and context: `subtypes TEXT[]`, `environments TEXT[]`, `roles TEXT[]`
- Flags and meta: `is_legendary BOOL`, `has_lair_actions BOOL`, `is_spellcaster BOOL`, `source TEXT`, `page INT`
- Derived fast flags: `is_flying BOOL`, `has_ranged BOOL`, `has_aoe BOOL`, `threat_tier SMALLINT`
- Speeds derived: `speed_walk INT`, `speed_fly INT`, `speed_swim INT`, `speed_climb INT`, `speed_burrow INT`
- Senses derived: `has_darkvision BOOL`, `darkvision_range INT`, `has_blindsight BOOL`, `blindsight_range INT`, `has_truesight BOOL`, `truesight_range INT`, `tremorsense_range INT`

Execution:
- Update `shared_models.Monster` with fields above.
- Create migration:
  - `python manage.py makemigration -m "monsters_add_recommended_columns"`
- Apply:
  - `python manage.py upgrade`
- Rebuild and smoke:
  - `python manage.py restart` (wait ~5s)
- Tests:
  - `./run_test.sh`

Acceptance:
- Existing tests green.
- POST/GET/PUT with new optional fields roundtrip.

---

## Iteration 2 — Spells: additive fields for fast filters (Done)
Goal: Add recommended fast-filter columns and metadata. Keep `distance` for BC.

DB/model changes (nullable, indexed where useful):
- Fast filters: `is_concentration BOOL` (duplicate of `concentration` for speed), `ritual BOOL`, `attack_roll BOOL`, `damage_type TEXT`, `save_ability TEXT`
- Targeting/AoE: `targeting TEXT`, `area JSONB` (already present; keep)
- Metadata: `source TEXT`, `page INT`, `name_ru TEXT`, `name_en TEXT`, `slug TEXT`
- Components: `components JSONB` may include `gp_cost INT`, `consumed BOOL` keys (no DB change; validation deferred)
- Keep `casting_time` as string for now; normalization later
- Keep `distance` and `range` side-by-side

Execution:
- Update `shared_models.Spell` with fields above.
- Migration:
  - `python manage.py makemigration -m "spells_add_fast_filters_and_metadata"`
- Apply:
  - `python manage.py upgrade`
- Rebuild and tests:
  - `python manage.py restart` (wait ~5s)
  - `./run_test.sh`

Acceptance:
- Old tests green.
- New fields persist/roundtrip.

Note:
- Completed and verified via curl.

---

## Iteration 3 — API: basic filters (Done)
Goal: Introduce simple filters using indexed scalar fields.

Monsters `/monsters/search`:
- Optional params: `type`, `size`, `cr_min`, `cr_max`, `is_flying`, `is_legendary`, `roles` (repeatable), `environments` (repeatable)
- Combine with existing name search
- Only AND conditions; sane defaults

Spells `/spells/search`:
- Optional params: `level`, `school`, `class` (public param; internally `klass`), `damage_type`, `save_ability`, `attack_roll`, `ritual`, `is_concentration`, `tags` (repeatable), `targeting`

Execution:
- Extend routers; keep existing behavior if no filters are passed.
- Add minimal API tests for filters.
- Restart and run tests.

Acceptance:
- Empty filters preserve current behavior.
- Filters compose correctly and are covered by tests.

Note:
- Implemented and manually verified via curl. Minimal API tests for filters to be added next.

---

## Iteration 4 — Derived values population (write-path + backfill) (Done)
Goal: Populate derived columns on create/update and backfill existing rows.

Monsters:
- `is_flying` from `speeds.fly > 0`
- `speed_*` from `speeds` JSON
- `has_darkvision`/`*_range` from `senses` JSON
- Optional heuristics (guarded by feature flag/env): `has_ranged`, `has_aoe`, `threat_tier` (keep logic minimal and documented)

Spells:
- `is_concentration` from `duration` string normalization (contains "Concentration")
- `damage_type`/`save_ability` from `damage`/`saving_throw` JSON if present
- `attack_roll` from presence of attack metadata (when available)

Execution:
- Add lightweight service/helpers in API layer to compute on write (no heavy parsing).
- Backfill migration (SQL UPDATEs) to set derived fields for existing rows.
- Restart and run tests.

Acceptance:
- Derived fields reflect sources; idempotent updates; tests green.
  - Implemented in API write-path for Monsters/Spells
  - Backfill migration applied successfully; all tests passed

---

## Iteration 5 — Indexing pass (Done)
Goal: Add indexes aligned with recommendations and observed filters.

- Note: Many B-Tree indexes for monster and spell fields were already created in Iteration 1/2 via model `index=True`. This pass focuses on additional indices (e.g., GIN/trgm) where needed.

- B-Tree: `cr`, `ac`, `hp`, `size`, `type`, `is_flying`, `is_legendary`, `is_spellcaster`, `threat_tier`, `level`, `school`, `is_concentration`, `ritual`, `damage_type`, `save_ability`
- GIN (ARRAY): `languages`, `damage_immunities`, `damage_resistances`, `damage_vulnerabilities`, `condition_immunities`, `environments`, `roles`, `classes`, `tags`
- Optional: GIN on JSONB (`speeds`, `senses`, `components`, `damage`, `area`, `saving_throw`) if needed
- Optional: pg_trgm on `name`, `name_ru`, `name_en` for fuzzy search

Execution:
- Alembic indices: explicit `op.create_index(..., postgresql_using='gin')` where needed.
- Restart and tests.

Acceptance:
- Migrations apply cleanly; query plans improved where relevant.
  - Added GIN indexes for ARRAY fields on `monster` and `spell`
  - Migration applied successfully; tests passed
  - Note: Indexes (GIN/trgm) are managed in migrations only; ORM metadata does not declare them. Alembic autogenerate is configured to ignore `_gin` indexes.

---

## Iteration 6 — Normalization and deprecation prep (Done)
Goal: Prepare migration path without breaking clients.

- Normalize `casting_time` to finite set: `action`, `bonus_action`, `reaction`, `1m`, `10m`, `1h`, `8h`
- Backfill `name` fields if required; generate `slug` (stable, lowercased, hyphenated)
- Legacy fields removal executed in subsequent step: `Monster.speed`, `Monster.speeds`, `Spell.distance` dropped.
- API responses may include both legacy and new fields with a deprecation note in docs

Execution:
- Lightweight normalization in write-path (`spells`: normalize `casting_time`, generate `slug`; `monsters`: generate `slug`).
- Backfill migration for `slug` and normalized `casting_time`.
- Docs updated with index management policy and deprecation prep note.

Acceptance:
- No breaking changes; tests green.
- Legacy fields preserved (`distance`, `speed`).

---

## Iteration 7 — Tightening constraints (post-observation) (Done)
Goal: Add enums and checks after data stabilizes.

- Wire existing enums into DB constraints where appropriate (e.g., `MonsterSize`); optionally check constraints for `Spell.level` (0..9)
- Consider uniqueness constraints as needed (e.g., `(slug)` or `(name, type)`) after data review — pending.

Execution:
- Added DB CHECKs via migration: `spell.level` in 0..9; `monster.size` and `monster.type` constrained to allowed sets (case-insensitive).
- Restarted and ran tests.

Acceptance:
- Constraints applied; existing tests green.

---

## Rollout Checklist (each iteration)
1) Code changes (minimal edits), add tests
2) `python manage.py makemigration -m "<short_message>"` (if DB changes)
3) `python manage.py upgrade`
4) `python manage.py restart` (wait ~5s)
5) `./run_test.sh`
6) Document any API surface changes or new filters

---

## Out of Scope (for now)
- Bot adjustments; will follow once API stabilizes and filters are finalized.
- Advanced full-text search/ranking.

---

## Post-Iteration Cleanup (Done)
- Removed legacy fields:
  - Monster: `speed` (INT), `speeds` (JSONB)
  - Spell: `distance` (INT)
- API and tests updated accordingly. Migrations applied.