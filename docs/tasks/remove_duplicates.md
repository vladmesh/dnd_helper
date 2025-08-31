## Duplicate Fields Cleanup — Proposal and Plan

Scope: Remove redundant/duplicated fields in the Spell model; keep the minimal set that supports current filters and data semantics without breaking API behavior. No changes are applied in this commit; this document defines the plan.

### Current Duplicates Identified

- Spell.concentration vs Spell.is_concentration
  - Background: `is_concentration` is derived from `duration` and is used for fast filtering (indexed). `concentration` is a parallel boolean in payload/tests but not used by search logic.
  - Proposal: Remove `concentration`, keep `is_concentration` (computed in write-path and backfilled in data migrations). Rationale: single source of truth (duration → is_concentration) and indexed filter already exists.
  - Impact: Update payloads/tests not to send/read `concentration`. Keep response model without `concentration`.

- Spell.caster_class vs Spell.classes
  - Background: `caster_class` (single enum) and `classes` (array of enums). Search uses `classes` (`/spells/search?class=...`). Many spells belong to multiple classes in 5e, so the array is the correct representation.
  - Proposal: Remove `caster_class`, keep `classes` as the canonical multi-class field.
  - Impact: Create/update endpoints should rely on `classes`. For backward compatibility, consider temporarily accepting `caster_class` in the payload and mapping it into `classes` until clients are updated (transition window), then fully drop it from the model.

- Spell.ritual defined twice in code
  - Background: The field is declared in the model twice (first without index, later with index); the DB has a single column and index.
  - Proposal: Keep a single `ritual` field definition with `index=True`. No DB change needed.

### Other Denormalizations Reviewed (Keep for now)

- Spell.damage_type vs Spell.damage JSON, Spell.save_ability vs Spell.saving_throw JSON
  - Purpose: denormalized scalar fields for fast filters; already indexed and used by `/spells/search`.
  - Decision: Keep.

- Monster.senses JSON vs derived flags/ranges (e.g., has_darkvision/darkvision_range), and is_flying vs speed_fly
  - Purpose: derived scalars enable simple and fast filters while preserving the raw JSON for display or future derivations.
  - Decision: Keep.

### Migration and Rollout Plan

All steps run inside containers via `manage.py`. Perform one step at a time, verify after each.

1) Code edits (minimal):
   - Remove `Spell.concentration` from the model and API update path; keep `is_concentration` derivation from `duration`.
   - Remove `Spell.caster_class` from the model and API handlers; rely on `classes` in payloads and filters.
   - Fix duplicate `Spell.ritual` attribute (leave one definition with `index=True`).

2) Data migration:
   - Backfill `classes` from `caster_class` prior to dropping the column (idempotent):
     - `UPDATE spell SET classes = CASE WHEN classes IS NULL THEN ARRAY[lower(caster_class::text)]::text[] ELSE array_cat(classes, ARRAY[lower(caster_class::text)]::text[]) END WHERE caster_class IS NOT NULL AND (classes IS NULL OR NOT (classes @> ARRAY[lower(caster_class::text)]::text[]));`
   - Drop column `caster_class`.
   - Drop column `concentration`.

3) Migrations and service cycle:
   - `python manage.py makemigration -m "remove_spell_duplicates"`
   - `python manage.py upgrade`
   - `python manage.py restart` (wait ~5s)

4) Tests and verification:
   - Update tests to remove `concentration` from payloads and ensure `classes` is provided/validated.
   - `./run_test.sh`
   - Manual smoke: `GET /spells`, `POST /spells` (with `classes`), `GET /spells/search?class=wizard&is_concentration=true`.

### Backward Compatibility Notes

- For a short transition period, the API can accept legacy `caster_class` in requests and map it to `classes` server-side (without persisting `caster_class`). This allows client updates to roll out safely before removing code paths.
- The `concentration` request field should be removed from clients. `is_concentration` will continue to be returned (and filterable) based on `duration`.

### Risks

- Client payloads relying on `concentration` or `caster_class` will fail validation after removal. Mitigate by adding a temporary compatibility layer before the drop, or coordinate client changes.
- Ensure that all existing rows have `classes` populated before dropping `caster_class`.

### Acceptance Criteria

- No references to `Spell.concentration` or `Spell.caster_class` remain in the codebase.
- Existing search filters continue to work (`class`, `is_concentration`, etc.).
- Migrations apply cleanly; tests pass.


