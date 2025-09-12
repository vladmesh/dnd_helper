## Filters UI Rework — Iterative Plan

### Goal
Simplify the list screens so they show:
- One button: “Add filters” (collapsed by default)
- One line of text: either “All monsters/All spells” or a readable summary of applied filters
- 8 entities per page

No backend changes in this task; implement purely in the bot UI (client-side filters retained). Keep changes minimal and consistent with the existing code structure and i18n policies.

### Non‑Goals
- No WebApp, no Inline Mode.
- No server‑side filters/pagination in this task (can be a later iteration if needed).
- Do not refactor unrelated parts; extend existing handlers/renderers.

### Constraints and Policies
- Use existing wrapped endpoints and i18n. No hardcoded UI strings; introduce i18n keys if missing and seed them via the established mechanism.
- Keep existing search flow intact (only lists are affected). Search can keep its current page size unless explicitly expanded later.
- Tests and any scripts should run inside containers using docker compose. Use manage.py helpers where applicable.

---

## Iteration 0 — Baseline and guardrails
- Confirm current list flows and where the UI is built:
  - Monsters list: `bot/src/dnd_helper_bot/handlers/monsters/render.py` (`render_monsters_list`) and callbacks in `handlers.py`.
  - Spells list: `bot/src/dnd_helper_bot/handlers/spells/render.py` (`render_spells_list`) and callbacks in `handlers.py`.
  - Pagination helper: `bot/src/dnd_helper_bot/utils/pagination.py`.
- Identify hardcoded page-size usages (notably "5") in list renderers and navigation logic.
- Verify existing “add submenu” state in monsters (`monsters_add_menu_open`) and plan analogous state for spells.

Acceptance criteria:
- A short document of the exact call-sites to update (inline code references are enough in PR description). No code changes yet.

---

## Iteration 1 — Page size: 8 entities per page (lists only)
- Introduce a single source of truth for list page size, without affecting search:
  - Add `PAGE_SIZE_LIST = 8` constant.
- Update monsters and spells list renderers to use the constant for slicing and nav math.
- Do not change the search flow.

Acceptance criteria:
- Monsters and spells lists display 8 items per page; navigation works correctly.

---

## Iteration 2 — Collapsed filters entry point
- Default (list) state:
  - Show single top button: `Add filters`.
  - Do not render filter rows by default.
- Manage view (filters screen): open on `Add filters` and show only filters UI (no entities).

Acceptance criteria:
- Collapsed state shows only the button above the list.
- Manage view shows only filters.

---

## Iteration 3 — Header text: “All …” or summary
- Header shows `All monsters/spells` if no applied filters, else a compact summary.
- Implement summary builders in renderers; use i18n labels.

Acceptance criteria:
- Header reflects applied state; no hardcoded strings.

---

## Iteration 4 — Apply-on-demand manage view (no mixed list+filters)
- While in manage view:
  - Show only filters UI and bottom button `Apply filters` (use `filters.apply`).
  - Do not update applied filters immediately; update only pending.
- On `Apply filters`:
  - Copy pending -> applied, close manage view, re-render list (filtered).
- In list state:
  - Top button label switches to `Change filters` if any filters are applied; otherwise `Add filters`.
  - Never show filters UI and entities at the same time.

Acceptance criteria:
- No screen contains both entity list and filters.
- Apply commits pending to applied and returns to list.

---

## Iteration 5 — Wire callbacks and polish
- Monsters: handle `mflt:add`, `mflt:apply`, `mflt:reset`, and field tokens; pending-only inside manage view.
- Spells: handle `sflt:add`, `sflt:apply`, `sflt:reset`, and field tokens; pending-only inside manage view.
- Keep page number reset to 1 on structural filter changes or apply; otherwise preserve current page.

Acceptance criteria:
- Callbacks work; transitions between list and manage are consistent.

---

## Iteration 6 — i18n keys in seed_data
- Add missing keys to `seed_data/seed_data_ui_translations.json`:
  - `list.all.monsters`, `list.all.spells`
  - `filters.change`
  - `filters.field.casting_time`, `filters.field.concentration`, `filters.field.class`
- Seeding execution is not part of this iteration (deferred).

Acceptance criteria:
- Seed files contain the required keys (en/ru).

---

## Iteration 7 — Documentation
- Update this plan to reflect manage view contract and button naming.
- Optional screenshots/GIF for PR.

Acceptance criteria:
- Docs reflect final UX precisely.

---

## Implementation Notes (file‑level pointers)
- Monsters:
  - `bot/src/dnd_helper_bot/handlers/monsters/handlers.py` — `monsters_filter_action`
  - `bot/src/dnd_helper_bot/handlers/monsters/render.py` — `render_monsters_list`, `_build_filters_keyboard`
- Spells:
  - `bot/src/dnd_helper_bot/handlers/spells/handlers.py` — `spells_filter_action`
  - `bot/src/dnd_helper_bot/handlers/spells/render.py` — `render_spells_list`, `_build_filters_keyboard`
- Shared:
  - `bot/src/dnd_helper_bot/utils/pagination.py` — introduce/use `PAGE_SIZE_LIST = 8`
  - Avoid touching search pagination unless explicitly required later

## Risk/Impact
- Changing page size touches pagination math; constrain changes to lists only and keep search intact.
- i18n additions required for new labels; ensure seeds are updated and idempotent.

## Follow‑ups (optional, later)
- Server‑side filters + pagination on API list endpoints, then switch bot to use them to avoid loading all items.
- Add compact per‑row “Hide” control in manage view if users need per‑field visibility toggling.


