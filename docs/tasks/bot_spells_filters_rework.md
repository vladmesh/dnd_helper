## Bot Spells Filters Rework — Iterative Plan

### Goals (from requirements)
- Remove the Apply button; filters must apply immediately on each press.
- Allow adding and removing filters (user controls in the bot UI).
- Default visible filters: spell level and school.
- Per-field UI pattern: one row per field. First button is "Any" (no filter). If "Any" is not selected, allow multi-select for set-like fields; for boolean fields enforce single-choice Yes/No when not Any.
- All button labels must use existing i18n mechanism (UI translation table). If new labels are needed, add them to the seeding script.

Notes and constraints:
- Keep existing endpoint usage and the i18n approach already adopted in the bot (no hardcoded strings). Primary list endpoint is `GET /spells/list/wrapped` with `?lang=`.
- Minimize changes to existing files; extend rather than refactor where possible.
- Client-side filtering only (same as current approach). Pagination remains client-side, page size unchanged.

---

## Current State (as of repo)
- Bot fetches spells via `GET /spells/list/wrapped` and builds a derived list for inline rendering.
- Keyboard is built in `bot/src/dnd_helper_bot/handlers/spells/render.py` (`_build_filters_keyboard`).
- Filter state is kept in `context.user_data` via helpers in `bot/src/dnd_helper_bot/handlers/spells/filters.py` with the notion of `pending` vs `applied` and an `Apply` button.
- Callback handler is implemented in `bot/src/dnd_helper_bot/handlers/spells/handlers.py` (`spells_filter_action`) and registered with prefix `^sflt:`.
- Existing spell filter set includes: Ritual (toggle), Concentration (toggle), Casting time sub-options (Bonus Action/Reaction, independent toggles), Level ranges (13/45/69, mutually exclusive). Has Apply/Reset actions.
- i18n keys exist for: `filters.ritual`, `filters.concentration`, `filters.cast.bonus`, `filters.cast.reaction`, `filters.level.13`, `filters.level.45`, `filters.level.69`, `filters.apply`, `filters.reset`. No `filters.any`, `filters.add`, `filters.remove`/`filters.hide`, `filters.yes`, `filters.no`, nor field-name keys like `filters.field.level`/`filters.field.school`/`filters.field.classes`.

---

## Target UX Specification
- Default visible filters (top to bottom):
  1) Spell level — multi-select among buckets: `1–3`, `4–5`, `6–9` (codes: `13`, `45`, `69`).
  2) School — multi-select among available schools. Use labels from API `labels` map inside each wrapped item; deduplicate and keep stable order.

- Additional filters that can be added/removed by the user:
  - Casting time — multi-select among "Bonus Action", "Reaction" (codes: `ba`, `re`). If both selected, require both.
  - Ritual — boolean with three-state UI: Any | Yes | No.
  - Concentration — boolean with three-state UI: Any | Yes | No.
  - Classes — multi-select among available classes. Use labels from API `labels.classes` or derive from wrapped items if present.

- Per-field row structure:
  - First button: `Any` with explicit field context for clarity. Label format: `Any <field>` where `<field>` is the localized filter name (e.g., `Any school`, `Any level`, `Any class`, `Any casting time`). For boolean fields (`Ritual`, `Concentration`) keep plain `Any` without the field suffix.
  - Next: options relevant for the field. If Any is not selected, allow multiple selections (except boolean fields where the choice is Any vs Yes vs No).
  - At the end of each active filter row, optionally include a small "Hide" control to remove this filter from the visible set (does not affect already applied state beyond clearing that field when removed). If a dedicated Manage submenu is implemented, the per-row hide control is optional.

- Manage filters (add/remove):
  - A compact top-row: `[+ Add]  [Reset]`.
    - `+ Add` opens an "Add filter" submenu listing filters not currently visible (e.g., Casting time, Ritual, Concentration, Classes). Selecting one enables the filter row with `Any` pre-selected.
    - `Reset` clears all filters to Any and restores the default visible set (Level, School only).

- Immediate application:
  - Any press on filter options updates state and re-renders the list immediately (no Apply button). Keep `Reset`.

- Navigation row remains the same (`Back`/`Next`) using existing i18n keys.

---

## State Model (context.user_data)
Extend the existing state while minimizing changes.

- Keep two dicts to avoid refactoring ripple, but update both at once to satisfy immediate application:
  - `spells_filters_pending: FiltersState`
  - `spells_filters_applied: FiltersState`

- `FiltersState` shape (proposed):
```python
{
  "level_buckets": set[str] | None,   # e.g., {"13", "45"} or None for Any
  "school": set[str] | None,          # school codes from API labels; None for Any
  "classes": set[str] | None,         # class codes; None for Any
  "casting_time": set[str] | None,    # subset of {"ba", "re"}; None/empty => Any
  "ritual": None | True | False,      # three-state
  "is_concentration": None | True | False, # three-state
  "visible_fields": list[str],        # order of rows, e.g., ["level_buckets", "school", ...]
}
```

Defaults:
- `visible_fields = ["level_buckets", "school"]`.
- All field values are `None` (Any) on first render.

Notes:
- For booleans: UI renders `Any | Yes | No` and stores one of {None, True, False}. This is the only field type where we do not allow multi-select beyond single Yes/No.
- For `casting_time`, use codes: `ba` → Bonus Action; `re` → Reaction.

---

## Callback Data Design
Prefix stays `sflt:` to avoid touching router registration.

- Manage UI:
  - `sflt:add` — open Add Filter submenu.
  - `sflt:add:<field>` — add field to `visible_fields` if not present, set it to Any (None), then re-render.
  - `sflt:rm:<field>` — remove field from `visible_fields` and clear its value (set to Any), then re-render.
  - `sflt:reset` — clear all values to Any; `visible_fields` = defaults.

- Field option toggles:
  - Level buckets: `sflt:lv:13|45|69` — toggle membership in `level_buckets` set; if becomes empty, treat as Any (set to None).
  - School: `sflt:sc:<code>` — toggle membership in `school` set; empty => None. Codes come from wrapped `labels.school` or the entity’s `school` value.
  - Classes: `sflt:cls:<code>` — toggle membership in `classes` set; empty => None.
  - Casting time: `sflt:ct:ba|re` — toggle membership in `casting_time` set; empty => None. If both selected, require both.
  - Boolean fields (ritual/concentration):
    - `sflt:rit:any` / `sflt:conc:any` — set to None (Any).
    - `sflt:rit:yes|no` / `sflt:conc:yes|no` — set True/False respectively (single choice).

Keyboard considerations:
- For fields with many options (e.g., classes), split options into multiple rows under the same field section while keeping the first row starting with `Any`.
- Keep callback data under Telegram limits (64 bytes); codes above are compact.

---

## Rendering Logic Updates
Files touched: `handlers/spells/render.py`, `handlers/spells/filters.py`, `handlers/spells/handlers.py`.

1) Replace the current `_build_filters_keyboard` with a generator that:
   - Renders the Manage row: `[+ Add] [Reset]`.
   - Iterates over `visible_fields` in order and renders each row as: `Any` + options (chunking into multiple rows if needed). For each active field row, optionally append a small `[Hide]` control at the end of the last row for this field.
   - Uses i18n for button labels:
     - Common: `filters.any`, `filters.add`, `filters.reset`, `filters.hide` (or `filters.remove`).
     - For booleans: `filters.yes`, `filters.no`.
     - For Level buckets: reuse `filters.level.13`, `filters.level.45`, `filters.level.69`. Any label uses `filters.field.level` to compose `Any <field>`.
     - For School options: use labels from API response `labels.school` (no new UI keys required for each school). Any label uses `filters.field.school` to compose `Any <field>`.
     - For Classes: use labels from API response `labels.classes`. Any label uses `filters.field.classes` to compose `Any <field>`.
     - For Casting time: reuse `filters.cast.bonus`, `filters.cast.reaction`. Any label uses `filters.field.casting_time`.

2) In `spells_filter_action`:
   - Remove `apply` handling entirely.
   - For any `sflt:*` toggle/update, update `pending`, then set `applied = pending` immediately.
   - Keep `reset` to clear and revert visible fields to defaults.
   - Keep current page if change is within the same filter category; reset to page=1 for structural changes (add/remove field or Any-to-some/empty-to-Any transitions) to avoid empty page issues.

3) In `_filter_spells`:
   - Update logic to handle set-based filters with OR semantics within a field and AND semantics across fields:
     - Level passes if `level_buckets is None` OR spell level falls into at least one selected bucket.
     - School passes if `school is None` OR spell school is in the selected set.
     - Classes pass if `classes is None` OR intersection between spell classes and selected set is non-empty.
     - Casting time passes if `casting_time is None` OR the spell’s `casting_time` indicates all selected sub-options (if both `ba` and `re` selected, require both; if only one selected, require that one).
     - Boolean passes if value is None OR equals the selected boolean.

---

## i18n / Seeding Changes (minimal)
Add only the keys that do not exist yet to `seeding/cli.py` `_default_ui_pairs()`:
- `filters.any`: RU "Любой", EN "Any". Any button will be composed with field name for non-boolean fields using: `filters.any` + space + the corresponding field label key (`filters.field.*`).
- `filters.add`: RU "Добавить фильтр", EN "Add filter".
- `filters.hide` (or `filters.remove`): RU "Убрать", EN "Hide" (choose one key, e.g., `filters.remove`).
- `filters.yes`: RU "Да", EN "Yes".
- `filters.no`: RU "Нет", EN "No".
- Field names for composition and Add submenu:
  - `filters.field.level`: RU "уровень", EN "level".
  - `filters.field.school`: RU "школа", EN "school".
  - `filters.field.classes`: RU "класс", EN "class" (pluralization is UI-level; keep compact key name).
  - `filters.field.casting_time`: RU "время накладывания", EN "casting time".
  - `filters.field.ritual`: RU "ритуал", EN "ritual".
  - `filters.field.concentration`: RU "концентрация", EN "concentration".

No changes needed for existing keys (`filters.reset`, `filters.level.*`, `filters.cast.*`, `filters.ritual`, `filters.concentration`).

---

## Iterations and Acceptance Criteria

### Iteration 1 — Remove Apply, immediate application; Default fields Level + School
- Keyboard:
  - Remove `Apply` button; keep `Reset`.
  - Add `filters.any` and use it as the first button in Level and School rows.
  - Render Level as multi-select buckets (13/45/69), OR semantics within field.
  - Render School row (initially empty list until schools are discovered from wrapped payload); first button `Any`, then available school labels/codes (chunked across rows if needed).
- State:
  - Introduce `level_buckets` and `school` sets (or None) and `visible_fields` default order.
  - On any toggle, update `pending` and immediately copy to `applied`.
- Filtering:
  - Implement set-based logic.
- i18n:
  - Add `filters.any` to seed; add field-name keys.
- Acceptance:
  - Toggling any filter updates the list immediately; pagination works; no Apply present.

### Iteration 2 — Add/Remove filters (Casting time, Ritual, Concentration, Classes)
- Keyboard:
  - Add top `[+ Add] [Reset]` row; implement Add submenu with Casting time, Ritual, Concentration, Classes.
  - Each added field gets its row with `Any` first. For booleans, render `Any | Yes | No`.
  - Optionally add row-level `[Hide]` control or rely solely on the Add submenu to toggle visibility (recommended: Add submenu + per-field Hide button).
- State:
  - Maintain `visible_fields` ordering; removing a field clears its value to Any.
- i18n:
  - Add `filters.add`, `filters.remove` (or `filters.hide`), `filters.yes`, `filters.no` to seed if not present.
- Acceptance:
  - Users can add Casting time/Ritual/Concentration/Classes and remove them. Filters apply instantly, list reflects selections.

### Iteration 3 — Polish and resilience
- Ensure callback data stays within limits; for large option sets (classes), split into multiple rows.
- Telemetry: structured logs on filter changes (field, action, sizes of result) using existing logger.

### Iteration 4 — Optional fields (Components, Damage, Saving Throw, Area)
- Add as multi-select with `Any` where applicable.
- Provide label resolution strategy:
  - If labels are (or can be) included in wrapped payload (`labels.components`, `labels.damage_type`, etc.), reuse them.
  - Otherwise, add minimal enum label coverage to API and seeding.

---

## Minimal Code Touch List
- `bot/src/dnd_helper_bot/handlers/spells/filters.py`
  - Extend `FiltersState` and helpers to support sets and three-state booleans; keep existing names and add new functions where necessary to avoid refactors.

- `bot/src/dnd_helper_bot/handlers/spells/handlers.py`
  - Update `spells_filter_action` to remove `apply` branch and to set `applied` immediately on any `sflt:` update. Add handling for `sflt:add`, `sflt:add:<field>`, `sflt:rm:<field>`.

- `bot/src/dnd_helper_bot/handlers/spells/render.py`
  - Replace `_build_filters_keyboard` with row-per-field rendering including `Any` and multi-select logic, plus Manage row. Use API labels for schools/classes from wrapped list.

- `seeding/cli.py`
  - Add the new UI keys (`filters.any`, `filters.add`, `filters.remove` or `filters.hide`, `filters.yes`, `filters.no`, and field-name keys under `filters.field.*`).

---

## Testing Plan (containers only)
- Unit-level (bot):
  - Pure functions for filter application (`_filter_spells`) with combinations of sets and booleans.
  - Keyboard builder: snapshot-like assertions on produced button texts and callback data (mock `t(...)`).

- Integration (bot + API):
  - Bring up compose; wait for services to be ready; seed minimal data.
  - Validate that toggling Level and School changes the number of listed items; navigation works; language switching keeps labels localized.

Acceptance checks:
- No hardcoded strings for user-facing buttons; all via `t(...)` or API-provided labels.
- `Apply` removed; `Reset` works; filters apply on every press.
- Defaults show Level and School; Add/Remove works for Casting time, Ritual, Concentration, Classes.

---

## Rollout and Rollback
- Rollout: ship seeding keys first; then bot changes. Keep feature small and behind minimal code paths.
- Rollback: if needed, re-enable the old keyboard builder (keep a guarded branch) and leave new i18n keys in place (harmless).

---

## Out of Scope (now)
- Server-side filtering or pagination.
- Deep links with preset filters.
- Inline Mode or WebApp UI.


