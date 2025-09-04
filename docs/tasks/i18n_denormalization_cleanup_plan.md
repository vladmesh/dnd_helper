## Multilingual and Denormalization Cleanup Plan (Monsters/Spells)

### Goal
Remove legacy multilingual text fields from base domain tables (`monster`, `spell`) so that only numeric fields and enum-backed fields remain there. All localized, human-readable text (names, descriptions, traits, actions, etc.) must live in translation tables (`monster_translations`, `spell_translations`). Align seed data and seeding scripts accordingly.

### Scope and Constraints
- Focus on: `monster`, `monster_translations`, `spell`, `spell_translations`, seed script (`seed.py`), and test data (`seed_data.json`).
- Out of scope: user-facing consistency or live data migration downtime minimization (non-prod only).
- Documentation and commit messages in English. Runtime work executed via docker compose and `manage.py`.

### High-Level Outcomes
- Base tables contain only numeric and enum fields (no localized text blobs).
- All localized text is stored per-language in translation tables with unique constraints.
- Seeding writes translations for both `ru` and `en` for all entities; missing English pieces are generated placeholders.
- Tests and seed data updated to reflect the new source of truth.

---

## Iteration 0 — Discovery (completed before this plan)
Objective: Review current models and confirm target shape.

- Confirmed models and enums present and aligned:
  - `shared_models/monster.py`, `shared_models/spell.py`
  - `shared_models/monster_translation.py`, `shared_models/spell_translation.py`
  - `shared_models/enums.py`
- Translation tables already modeled to hold localized text (`name`, `description`; and for monsters also `traits`, `actions`, `reactions`, `legendary_actions`, `spellcasting`).
- No production data to migrate; database content is seeded from `seed.py` and `seed_data.json`.

---

## Iteration 1 — Drop legacy localized fields from base tables (schema change)
Objective: Remove multilingual text from base tables so only numeric/enum fields remain there for localized content.

- Monster table: drop columns
  - `name`, `description`, `name_ru`, `name_en`
  - Localized JSON blobs: `traits`, `actions`, `reactions`, `legendary_actions`, `spellcasting`
- Spell table: drop columns
  - `name`, `description`, `name_ru`, `name_en`
- Enforce non-null on translations where applicable:
  - `monster_translations.name` and `spell_translations.name` NOT NULL
  - Optionally, set `description` to NOT NULL with default empty string if we want stricter guarantees
- Keep non-i18n metadata fields intact for now (e.g., `slug`, `source`, `range`, `casting_time`, `alignment`, etc.). They will be normalized in later iterations.

Commands:
```bash
python3 manage.py makemigration -m "i18n: drop localized fields from base tables"
python3 manage.py upgrade
```

---

## Iteration 2 — Update seed data and seeding logic
Objective: Align `seed.py` and `seed_data.json` with the new source of truth.

- `seed_data.json`:
  - For each monster/spell, remove base `name`/`description` fields and ensure `monster_translations`/`spell_translations` entries include both `ru` and `en` names and descriptions.
  - For monsters, move localized `traits`, `actions`, `reactions`, `legendary_actions`, `spellcasting` into `monster_translations` objects.
  - Generate English placeholders where missing (this is acceptable for tests).
  - Ensure enum-coded fields use canonical enum values (e.g., `monster.size = "medium"`, `monster.type = "humanoid"`, `spell.school = "conjuration"`, etc.).
- `seed.py`:
  - Write/update upsert logic to populate base tables first (numeric/enum fields only), then per-language translation rows.
  - Remove usage of dropped base fields (`name`, `description`, and monster localized blobs) and switch to translation upserts.
  - Keep operation idempotent (upsert by natural keys like `slug` + `lang`).
- Tests:
  - Adjust any test fixtures and API client expectations to read localized fields from translations.

Commands:
```bash
python3 manage.py restart
python3 manage.py upgrade
```

Notes:
- After container restarts, allow a brief wait before requests.

---

## Iteration 3 — Finalize constraints and tests
Objective: Tighten constraints and ensure tests reflect translation source of truth.

- Enforce NOT NULL on translation `name` fields; consider `description` NOT NULL with empty-string default if desired.
- Ensure indexes where useful on frequently filtered numeric/enum fields.
- Update tests (API/bot) to assert name/description via translations, not base tables.

Commands:
```bash
python3 manage.py makemigration -m "i18n: finalize constraints"
python3 manage.py upgrade
```

---

## Data Model Target (post-cleanup)
- `monster` table: numeric and enum fields only; no localized text. Examples:
  - Numeric: `hp`, `ac`, `xp`, `speed_*`, `darkvision_range`, etc.
  - Enums/enum arrays: `cr`, `type`, `size`, `environments[]`, `roles[]`.
  - Identifiers/keys allowed: `id`, `slug`.
- `monster_translations` table: `name`, `description`, plus localized `traits`, `actions`, `reactions`, `legendary_actions`, `spellcasting` per `lang`.
- `spell` table: numeric and enum fields only; no localized text. Examples:
  - Numeric: `level`, `page`.
  - Enums/enum arrays: `school`, `classes[]`, `damage_type`, `save_ability`, `targeting`.
  - Identifiers/keys allowed: `id`, `slug`.
- `spell_translations` table: `name`, `description` per `lang`.

---

## Rollback Strategy
- Drops are isolated to a single iteration; if needed, re-add dropped columns in a follow-up migration.

## Operational Notes
- Always run operations inside containers using `docker compose` via `manage.py` commands where available.
- Keep migrations small; prefer many simple revisions over one large change.
- After restarting containers or applying migrations, wait a few seconds before hitting services.

## Deliverables
- Alembic migration dropping localized fields from base tables and finalizing constraints.
- Updated `seed.py` to upsert base records and per-language translations only.
- Updated `seed_data.json` with full `ru`/`en` localized content for all entries.
- Adjusted tests to the new structure.


