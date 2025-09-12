## Monsters & Spells Model Normalization Plan

### Context and goals
- Normalize monsters and spells models so that monster/spell base tables contain only:
  - numbers, booleans, enum codes, and identifiers (e.g., slug)
  - structured JSON with numeric/enum values where appropriate
- Move all human-readable text to translation tables (`MonsterTranslation`, `SpellTranslation`).
- Remove redundant/unused derived fields that bloat the schema and are not used by queries.

### Non-goals
- No UI/UX redesign.
- No business logic changes beyond making fields consistent and moving text into translations.
- No performance tuning beyond indexes directly affected by changed fields.

### Terminology clarification
- ability scores: STR/DEX/CON/INT/WIS/CHA (numbers) — stay on monster base entity as numeric values.
- skills: numeric bonuses keyed by skill name — stay on monster base entity (keys validated against enum).
- abilities in prose (monster features like “Pounce”) — text blocks; stay in `MonsterTranslation.traits/actions/...`.

### High-level changes summary
- Remove unused flags: `has_ranged`, `has_aoe` from `Monster`.
- Remove senses-derived fields from `Monster` (`has_darkvision`, `darkvision_range`, `has_blindsight`, `blindsight_range`, `has_truesight`, `truesight_range`, `tremorsense_range`). Keep only `senses` JSONB.
- Move `Monster.languages` (textual) to `MonsterTranslation` as a new text field (e.g., `languages_text`).
- Rename `Monster.abilities` → `ability_scores` to avoid ambiguity; keep numeric values; validate keys via existing `Ability` enum.
- Introduce `Skill` enum and validate keys of `skills` and `saving_throws`.
- Convert string fields to enums where enums already exist:
  - `Monster.type` → `MonsterType`, `Monster.size` → `MonsterSize` (keep existing `cr: DangerLevel`).
  - `Monster.damage_*` and `condition_immunities` → arrays of `DamageType` / `Condition`.
  - Spells: ensure `damage_type`, `save_ability`, `targeting` use enums (`DamageType`, `Ability`, `Targeting`).
- Fix `Spell.ritual` duplicate declaration (single boolean field; indexed where useful).
- Optional (if/when needed): introduce normalized numeric helpers (`range_feet`, `casting_time_normalized`) while keeping textual forms in translations.

### Iteration 1 — Remove unused/derived monster fields
Scope
- Remove `Monster.has_ranged`, `Monster.has_aoe`.
- Remove senses-derived fields and their calculation in API (`_compute_monster_derived_fields`). Keep only `monster.senses` JSONB.

DB migration
- Drop columns: `has_ranged`, `has_aoe`, `has_darkvision`, `darkvision_range`, `has_blindsight`, `blindsight_range`, `has_truesight`, `truesight_range`, `tremorsense_range`.
- Drop related indexes.

Code edits
- Delete assignments for removed fields in `routers/monsters/derived.py`; keep `is_flying` computation from speeds.
- Ensure schemas and response models do not reference removed fields.

Seeds/data
- Remove deleted fields from `seed_data_monsters.json`.

Testing
- API smoke and monsters handlers tests should still pass; add regression test that `senses` remains populated and no derived fields are present.

Risks
- Low; fields are not used by tests or handlers. Seed diffs required.

### Iteration 2 — Move languages from monster base to translations
Scope
- Move textual monster languages from `Monster.languages` to `MonsterTranslation.languages_text`.

DB migration
- Add `languages_text TEXT NULL` to `monster_translations`.
- Backfill: for each monster having `languages`, copy serialized string (or joined list) into translations in both available languages when possible; otherwise fill primary language only.
- Drop `Monster.languages` and its index.

Code edits
- Update wrapped endpoints to include `languages_text` from translation; raw endpoints keep base entity unchanged.

Seeds/data
- Remove `languages` from monster seeds; add `languages_text` under each translation where we have data.

Testing
- Verify wrapped monsters include `translation.languages_text`.
- Verify no `languages` field on base entity in raw responses.

Risks
- Low/medium: requires careful data backfill to avoid losing language info.

### Iteration 3 — Clarify and validate ability scores and skills
Scope
- Rename `Monster.abilities` → `ability_scores`.
- Introduce `Skill` enum; validate keys for `skills` and `saving_throws` (and keep values numeric).

DB migration
- Rename column `abilities` → `ability_scores` (or add new column + backfill + drop old if rename not safe).

Code edits
- Add validators coercing keys to enums (`Ability` for ability scores; `Skill` for skills; `Ability` for saving throws’ keys if stored as dict keys).
- Keep UI labels sourced from enum translations (`enum_labels` utility).

Seeds/data
- Rename keys in seeds accordingly; ensure keys conform to enums.

Testing
- Add unit tests for validators (invalid keys fail fast; valid keys pass).

Risks
- Medium: rename touches seeds and any code that accesses `abilities`.

### Iteration 4 — Monster enums and arrays normalization
Scope
- Convert `Monster.type` and `Monster.size` to enums (`MonsterType`, `MonsterSize`).
- Convert `damage_immunities`, `damage_resistances`, `damage_vulnerabilities` to arrays of `DamageType`.
- Convert `condition_immunities` to arrays of `Condition`.
- Optional: add `language_codes CreatureLanguage[]` for later filtering (leave unfilled if no parser yet).

DB migration
- Alter column types to store enum codes (TEXT) with validators on the model side.
- Rebuild indexes (btree for enums; GIN for arrays where useful).

Code edits
- Validators to coerce stored strings into enum instances on serialization.

Seeds/data
- Ensure seed arrays contain valid enum codes only.

Testing
- Add integration tests for filters over enums/arrays if such filters exist.

Risks
- Medium: requires seed cleanup and enum coverage.

### Iteration 5 — Spells cleanup and enum enforcement
Scope
- Fix duplicate `Spell.ritual` (leave a single boolean; index if used by filters).
- Enforce enums: `damage_type: DamageType`, `save_ability: Ability`, `targeting: Targeting`.
- Keep textual `material` and long descriptions in `SpellTranslation`; consider adding optional normalized helpers (`range_feet`, `casting_time_normalized`) later.

DB migration
- Drop duplicate ritual column if present; ensure a single `ritual` exists.
- Adjust columns to enum-validated text where needed.

Code edits
- Validators for coercion to enums.

Seeds/data
- Remove duplicate ritual in seeds; ensure enum codes are valid.

Testing
- Extend spell handler tests for ritual and enums.

Risks
- Medium: one-time schema clean-up; straightforward.

### Iteration 6 — Index policy alignment
Scope
- Add GIN jsonb_path_ops index to `Monster.senses` for advanced queries (only if needed).
- Ensure btree indexes exist for frequently-filtered enums and booleans.

DB migration
- Create/drop indexes per usage; keep complex GIN indexes only if queries need them.

Testing
- Verify query plans in integration tests (optional).

### Operational checklist per iteration
- Rebuild/restart containers prior to migrations.
- Run migrations inside API container.
- Reseed if needed (only the affected pieces).
- Wait for services to become healthy before tests.

### Acceptance criteria (per iteration)
- All service tests green (API and Bot test suites as applicable).
- No references to removed fields in code, docs, seeds.
- API responses (raw/wrapped) align with architecture/i18n policy.

### Rollback strategy
- Each iteration uses a single reversible migration.
- Keep backups of seeds and provide downgrade steps in Alembic.

### Follow-ups (optional)
- Add `Alignment` enum when finalized.
- Add `CreatureLanguage` enum and `Monster.language_codes[]` when we need language-based filters.
- Consider `range_feet` and `casting_time_normalized` for spells if numeric filtering proves useful.


