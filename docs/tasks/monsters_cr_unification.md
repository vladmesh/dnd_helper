## Monsters CR/Danger Level Unification — Implementation Plan

### Decision
- Keep field: `cr` (canonical DnD field)
- Remove field: `dangerous_lvl`
- Reuse enum `DangerLevel` to represent CR domain values exactly: "1/8", "1/4", "1/2", "1", "2", ..., "30"

Rationale:
- "CR" is the standard domain name and is already used throughout data and docs.
- Eliminates duplication and confusion between `cr` and `dangerous_lvl` while keeping API semantics clear.

### Incremental Iterations

#### Iteration 1 — Introduce CR enum and parallel field (non-breaking)
- Add a temporary enum `ChallengeRating` in `shared_models.enums` with values: "1/8", "1/4", "1/2", "1", "2", ..., "30".
- Add optional field `cr_enum: Optional[ChallengeRating]` to `shared_models.monster.Monster` and DB (text/varchar, indexed).
- Keep existing fields `dangerous_lvl` and numeric `cr` unchanged.
- Update seeding (`seed_from_dtn.py`) to also populate `cr_enum` from numeric `cr` via mapping:
  - `0.125 → "1/8"`, `0.25 → "1/4"`, `0.5 → "1/2"`, integers `1..30 → "1".."30"`.
- Expose `cr_enum` in API responses in addition to existing fields (no removals); mark `dangerous_lvl` as deprecated in docs.
- Tests: add coverage that `cr_enum` is present and correctly mapped in seed and list/detail endpoints.
- Docs: document `cr_enum` and deprecate `dangerous_lvl` (no removals yet).

Operational checklist (inside containers):
1) `python manage.py restart`
2) Wait ~5 seconds
3) Create and apply migration to add `cr_enum` column (nullable, indexed)
4) Update seed to fill `cr_enum`; re-seed if needed
5) Update API serialization to include `cr_enum`
6) Update docs/tests; run linters and tests

#### Iteration 2 — Switch consumers to CR enum (still non-breaking)
- Update bot and API UI layers to display/use `cr_enum` instead of numeric `cr` or `dangerous_lvl`.
- Keep `dangerous_lvl` and numeric `cr` present for compatibility (still populated).
- Tests: adjust expectations to prefer `cr_enum` in outputs; keep backward-compatible assertions where necessary.
- Docs: `cr_enum` becomes the primary documented field; `dangerous_lvl` and numeric `cr` marked as deprecated (to be removed in Iteration 3).

Operational checklist:
1) `python manage.py restart`
2) Wait ~5 seconds
3) Update views/serializers/clients to use `cr_enum`
4) Update tests and docs; run linters and tests

#### Iteration 3 — Consolidate: single `cr` with `DangerLevel`, drop legacy
- Reuse the enum name `DangerLevel` to represent CR values (replace temporary `ChallengeRating`).
- Model changes:
  - Delete field: `dangerous_lvl` from model and DB.
  - Change `cr: Optional[float]` → `cr: Optional[DangerLevel] = Field(index=True)`.
  - Remove temporary field `cr_enum` from model and DB.
- Alembic migration:
  - Drop column `dangerous_lvl`.
  - Alter `cr` column type from numeric to text/varchar; backfill `cr` from `cr_enum` values.
  - Drop column `cr_enum`.
  - Validate that all `cr` values belong to the enum domain.
- Seeding: write `cr` using `DangerLevel` members (no floats), remove any `dangerous_lvl` logic.
- API contract: `cr` is the only field; enum-string domain. Remove `dangerous_lvl` and `cr_enum` from responses.
- Docs: update `docs/fields.md` to `cr` as enum-string; remove mentions of `dangerous_lvl` and `cr_enum`.
- Tests: update to expect only enum-string `cr`.

Operational checklist:
1) `python manage.py restart`
2) Wait ~5 seconds
3) Implement enum/model changes and generate migration
4) Implement backfill and apply migration
5) Update seed, docs, and tests; run linters and tests

### Rollback Plan
- Each migration is reversible:
  - Iteration 1: drop `cr_enum` if needed.
  - Iteration 3: downgrade restores numeric `cr`, re-adds `dangerous_lvl` and `cr_enum` (nullable), best-effort backfill.

### Out of Scope
- Any changes unrelated to CR/danger level unification.


