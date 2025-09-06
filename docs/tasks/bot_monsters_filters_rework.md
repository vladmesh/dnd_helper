## Bot Monsters Filters Rework — Iterative Plan

### Goals (from requirements)
- Remove the Apply button; filters must apply immediately on each press.
- Allow adding and removing filters (user controls in the bot UI).
- Default visible filters: danger level (CR) and monster type.
- Per-field UI pattern: one row per field. First button is "Any" (no filter). Then the list of options. If "Any" is not selected, multiple options can be selected at the same time (see boolean nuance below).
- All button labels must use existing i18n mechanism (UI translation table). If new labels are needed, add them to the seeding script.

Notes and constraints:
- Keep existing endpoint usage and the i18n approach already adopted in the bot (no hardcoded strings). Primary list endpoint is `GET /monsters/list/wrapped` with `?lang=`.
- Minimize changes to existing files; extend rather than refactor where possible.
- Client-side filtering only (same as current approach). Pagination remains client-side, page size unchanged.

---

## Current State (as of repo)
- Bot fetches monsters via `GET /monsters/list/wrapped` and builds a derived list for inline rendering.
- Keyboard is built in `bot/src/dnd_helper_bot/handlers/monsters/render.py` (`_build_filters_keyboard`).
- Filter state is kept in `context.user_data` via helpers in `bot/src/dnd_helper_bot/handlers/monsters/filters.py` with the notion of `pending` vs `applied` and an `Apply` button.
- Callback handler is registered in `bot/src/dnd_helper_bot/main.py` (pattern `^mflt:`) and implemented in `bot/src/dnd_helper_bot/handlers/monsters/handlers.py` (`monsters_filter_action`).
- Existing monster filter set includes: Legendary (toggle), Flying (toggle), CR ranges (03/48/9p, mutually exclusive), Size (S/M/L, mutually exclusive), Apply/Reset actions.
- i18n keys for filters exist for several options (e.g., `filters.legendary`, `filters.flying`, `filters.cr.*`, `filters.size.*`, `filters.reset`, `filters.apply`). No `filters.any`, `filters.add`, `filters.remove`, `filters.yes`, `filters.no` yet.

---

## Target UX Specification
- Default visible filters (top to bottom):
  1) Danger level (CR) — multi-select among buckets: `0–3`, `4–8`, `9+` (codes: `03`, `48`, `9p`).
  2) Monster type — multi-select among available types. Use labels from API `labels` map inside wrapped list.

- Additional filters that can be added/removed by the user:
  - Size — multi-select among `S`, `M`, `L` (labels via UI translations as in current code).
  - Flying — boolean with three-state UI: Any | Yes | No. Note: for boolean fields, "multi-select" has no semantic value, so enforce single-choice Yes/No when not Any.
  - Legendary — boolean (same pattern as Flying).
  - (Optional, later) Roles, Environments — multi-select; labels would require enum/i18n coverage.

- Per-field row structure:
  - First button: `Any`. Selecting it clears the field filter (no restriction applied for this field).
  - Next: options relevant for the field. If Any is not selected, allow multiple selections (except boolean fields where the choice is Any vs Yes vs No).
  - At the end of each active filter row, include a small "Hide"/"Remove" control to remove this filter from the visible set (does not affect already applied state beyond clearing that field when removed). This control is optional if we provide a dedicated Manage screen — see below.

- Manage filters (add/remove):
  - A compact top-row: `[+ Add]  [Reset]`.
    - `+ Add` opens an "Add filter" submenu listing filters not currently visible (e.g., Size, Flying, Legendary; later Roles, Environments). Selecting one enables the filter row with `Any` pre-selected.
    - `Reset` clears all filters to Any and restores the default visible set (CR, Type only).
  - Alternatively (if avoiding an extra submenu): render a separate "Manage" row with buttons for each available filter to toggle its visibility. However, a submenu keeps the main list more compact; we target the submenu approach.

- Immediate application:
  - Any press on filter options updates state and re-renders the list immediately (no Apply button). Keep `Reset`.

- Navigation row remains the same (`Back`/`Next`) using existing i18n keys.

---

## State Model (context.user_data)
Extend the existing state while minimizing changes.

- Keep two dicts to avoid refactoring ripple, but update both at once to satisfy immediate application:
  - `monsters_filters_pending: FiltersState`
  - `monsters_filters_applied: FiltersState`

- `FiltersState` shape (proposed):
```python
{
  "types": set[str] | None,        # None -> Any; else a set of type codes
  "cr_buckets": set[str] | None,   # e.g., {"03", "48"} or None for Any
  "sizes": set[str] | None,        # e.g., {"S", "M"} or None
  "flying": None | True | False,   # three-state
  "legendary": None | True | False,# three-state
  "visible_fields": list[str],     # order of rows, e.g., ["cr_buckets", "types", ...]
}
```

Defaults:
- `visible_fields = ["cr_buckets", "types"]`.
- All field values are `None` (Any) on first render.

Notes:
- For booleans: UI renders `Any | Yes | No` and stores one of {None, True, False}. This is the only field type where we do not allow multi-select beyond single Yes/No.

---

## Callback Data Design
Prefix stays `mflt:` to avoid touching router registration.

- Manage UI:
  - `mflt:add` — open Add Filter submenu.
  - `mflt:add:<field>` — add field to `visible_fields` if not present, set it to Any (None), then re-render.
  - `mflt:rm:<field>` — remove field from `visible_fields` and clear its value (set to Any), then re-render.
  - `mflt:reset` — clear all values to Any; `visible_fields` = defaults.

- Field option toggles:
  - CR buckets: `mflt:cr:03|48|9p` — toggle membership in `cr_buckets` set; if becomes empty, treat as Any (set to None).
  - Types: `mflt:type:<code>` — toggle membership in `types` set; empty => None.
  - Sizes: `mflt:sz:S|M|L` — toggle membership in `sizes` set; empty => None.
  - Boolean fields (flying/legendary):
    - `mflt:fly:any` / `mflt:leg:any` — set to None (Any).
    - `mflt:fly:yes|no` / `mflt:leg:yes|no` — set True/False respectively (single choice).

Keyboard considerations:
- For fields with many options (e.g., types), split options into multiple rows under the same field section while keeping the first row starting with `Any`.
- Keep callback data under Telegram limits (64 bytes); codes above are compact.

---

## Rendering Logic Updates
Files touched: `handlers/monsters/render.py`, `handlers/monsters/filters.py`, `handlers/monsters/handlers.py`.

1) Replace the current `_build_filters_keyboard` with a generator that:
   - Renders the Manage row: `[+ Add] [Reset]`.
   - Iterates over `visible_fields` in order and renders each row as: `Any` + options (chunking into multiple rows if needed). For each active field row, optionally append a small `[Hide]` control at the end of the last row for this field.
   - Uses i18n for button labels:
     - Common: `filters.any`, `filters.add`, `filters.reset`, `filters.hide` (or `filters.remove`).
     - For booleans: `filters.yes`, `filters.no`.
     - For CR: reuse `filters.cr.03`, `filters.cr.48`, `filters.cr.9p`.
     - For Size: reuse `filters.size.S`, `filters.size.M`, `filters.size.L`.
     - For Type options: use labels from API response `labels` (no new UI keys required for each type).

2) In `monsters_filter_action`:
   - Remove `apply` handling entirely.
   - For any `mflt:*` toggle/update, update `pending`, then set `applied = pending` immediately.
   - Keep `reset` to clear and revert visible fields to defaults.
   - Keep current page if change is within the same filter category; reset to page=1 for structural changes (add/remove field or Any-to-some/empty-to-Any transitions) to avoid empty page issues.

3) In `_filter_monsters`:
   - Update logic to handle set-based filters with OR semantics within a field and AND semantics across fields:
     - CR passes if `cr_buckets is None` OR monster CR falls into at least one selected bucket.
     - Type passes if `types is None` OR monster type is in the selected set.
     - Size passes if `sizes is None` OR monster size is in the selected set.
     - Boolean passes if value is None OR equals the selected boolean.

---

## i18n / Seeding Changes (minimal)
Add only the keys that do not exist yet to `seeding/cli.py` `_default_ui_pairs()`:
- `filters.any`: RU "Любой", EN "Any".
- `filters.add`: RU "Добавить фильтр", EN "Add filter".
- `filters.hide` (or `filters.remove`): RU "Убрать", EN "Hide" (choose one key, e.g., `filters.remove`).
- `filters.yes`: RU "Да", EN "Yes".
- `filters.no`: RU "Нет", EN "No".

No changes needed for existing keys (`filters.reset`, `filters.cr.*`, `filters.size.*`, `filters.legendary`, `filters.flying`).

---

## Iterations and Acceptance Criteria

### Iteration 1 — Remove Apply, immediate application; Default fields CR + Type
- Keyboard:
  - Remove `Apply` button; keep `Reset`.
  - Add `filters.any` and use it as the first button in CR row.
  - Render CR as multi-select buckets (03/48/9p), OR semantics within field.
  - Render Type row (initially empty list until types are discovered from wrapped payload); first button `Any`, then available type labels/codes (chunked across rows if needed).
- State:
  - Introduce `types` and `cr_buckets` sets (or None) and `visible_fields` default order.
  - On any toggle, update `pending` and immediately copy to `applied`.
- Filtering:
  - Implement set-based logic.
- i18n:
  - Add `filters.any` to seed.
- Acceptance:
  - Toggling any filter updates the list immediately; pagination works; no Apply present.

### Iteration 2 — Add/Remove filters (Size, Flying, Legendary)
- Keyboard:
  - Add top `[+ Add] [Reset]` row; implement Add submenu with Size, Flying, Legendary (omit Roles/Environments for now).
  - Each added field gets its row with `Any` first. For booleans, render `Any | Yes | No`.
  - Add row-level `[Hide]` control or rely solely on the Add submenu to toggle visibility (pick one for simplicity; recommended: Add submenu + per-field Hide button).
- State:
  - Maintain `visible_fields` ordering; removing a field clears its value to Any.
- i18n:
  - Add `filters.add`, `filters.remove` (or `filters.hide`), `filters.yes`, `filters.no` to seed.
- Acceptance:
  - Users can add Size/Flying/Legendary and remove them. Filters apply instantly, list reflects selections.

### Iteration 3 — Polish and resilience
- Persist discovered type options within the current session to avoid rebuilding from scratch on every render.
- Ensure callback data stays within limits; if the types set is large, consider limiting to top-N by frequency or adding a paging submenu (out of scope unless needed).
- Telemetry: structured logs on filter changes (field, action, sizes of result) using existing logger.

### Iteration 4 — Optional fields (Roles, Environments)
- Add as multi-select with `Any`.
- Provide label resolution strategy:
  - If labels are (or can be) included in wrapped payload (`labels.roles`, `labels.environments`), reuse them.
  - Otherwise, add minimal enum label coverage to API and seeding.

---

## Minimal Code Touch List
- `bot/src/dnd_helper_bot/handlers/monsters/filters.py`
  - Extend `FiltersState` and helpers to support sets and three-state booleans; keep existing names and add new functions where necessary to avoid refactors.

- `bot/src/dnd_helper_bot/handlers/monsters/handlers.py`
  - Update `monsters_filter_action` to remove `apply` branch and to set `applied` immediately on any `mflt:` update.
  - Add handling for `mflt:add`, `mflt:add:<field>`, `mflt:rm:<field>`.

- `bot/src/dnd_helper_bot/handlers/monsters/render.py`
  - Replace `_build_filters_keyboard` with row-per-field rendering including `Any` and multi-select logic, plus Manage row.
  - Use API labels for types from wrapped list; cache per session if needed.

- `seeding/cli.py`
  - Add the new UI keys (`filters.any`, `filters.add`, `filters.remove` or `filters.hide`, `filters.yes`, `filters.no`).

---

## Testing Plan (containers only)
- Unit-level (bot):
  - Pure functions for filter application (`_filter_monsters`) with combinations of sets and booleans.
  - Keyboard builder: snapshot-like assertions on produced button texts and callback data (mock `t(...)`).

- Integration (bot + API):
  - Bring up compose; wait for services to be ready; seed minimal data.
  - Validate that toggling CR and Type changes the number of listed items; navigation works; language switching keeps labels localized.

Acceptance checks:
- No hardcoded strings for user-facing buttons; all via `t(...)` or API-provided labels.
- `Apply` removed; `Reset` works; filters apply on every press.
- Defaults show CR and Type; Add/Remove works for Size/Flying/Legendary.

---

## Rollout and Rollback
- Rollout: ship seeding keys first; then bot changes. Keep feature small and behind minimal code paths.
- Rollback: if needed, re-enable the old keyboard builder (keep a guarded branch) and leave new i18n keys in place (harmless).

---

## Out of Scope (now)
- Server-side filtering or pagination.
- Deep links with preset filters.
- Inline Mode or WebApp UI.


