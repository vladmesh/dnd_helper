## Bot Inline Filters + Pagination: Iterative Plan

### Scope
- Implement inline filters with InlineKeyboard and pagination for full lists of spells and monsters.
- Add “Quick filters” row above the list.
- No WebApp, no Inline Mode. Deep links with presets are out of current scope (planned for a later iteration).

### Current State (as of repo)
- API:
  - Spells: `GET /spells` (full list), `GET /spells/{id}`, `GET /spells/search` (requires q, supports several filters; no pagination params).
  - Monsters: `GET /monsters` (full list), `GET /monsters/{id}`, `GET /monsters/search` (requires q; no pagination params).
- Bot:
  - Lists load the entire dataset via `api_get("/spells")` or `api_get("/monsters")` and paginate client‑side (`utils.pagination.paginate`, page size 5).
  - No filter UI yet. Callback data is simple (`spell:list:page:N`, etc.).

### Non‑Goals (now)
- Inline Mode, WebApp forms, or free‑text multi‑param parsing.
- Preset deep links (to be done in a later task).

---

## Iteration 1 — Spells: Quick Filters (client‑side), InlineKeyboard, pagination
Deliver a fully working list with quick inline filters, without touching the backend.

- UI/UX
  - Top row: Quick filters and actions.
    - Ritual (toggle)
    - Concentration (toggle)
    - Casting time shortcuts: Bonus, Reaction (toggles)
    - Level ranges: 1–3, 4–5, 6–9 (mutually exclusive shortcuts)
    - Actions: Apply, Reset
  - List area: current page (5 items) with per‑item “Details”.
  - Navigation row: Back | Page N | Next (enable/disable based on client‑side filtered length).

- State
  - Keep per‑chat/per‑message filter state in `context.user_data["spells_filters"]` with a compact dict:
    - `{ ritual: bool|None, is_concentration: bool|None, cast: { bonus: bool, reaction: bool }, level_range: "1-3"|"4-5"|"6-9"|None, page: int }`.
  - Apply filters client‑side to the already fetched list from `/spells`.

- Callback data (compact, within 64 bytes)
  - `sflt:rit` (toggle Ritual)
  - `sflt:conc` (toggle Concentration)
  - `sflt:ct:ba` / `sflt:ct:re` (toggle Bonus/Reaction)
  - `sflt:lv:13` / `sflt:lv:45` / `sflt:lv:69` (set level range) or `sflt:lv:clr`
  - `sflt:apply`, `sflt:reset`
  - Pagination: `spell:list:page:N` (reused)

- Filtering logic (client‑side)
  - Ritual: `spell.ritual == True` if enabled.
  - Concentration: `spell.is_concentration == True` if enabled.
  - Casting time: match normalized `casting_time` values `bonus_action` / `reaction` (already normalized in API on write/update).
  - Level ranges: `level in {1,2,3}` etc.

- Acceptance criteria
  - From the main menu, user can open Spells list, toggle filters, apply/reset, navigate pages; results reflect filters immediately.
  - Single message is edited in place; no message spam.
  - Callback data stays under 64 bytes.

- Testing
  - Manual happy paths with combinations of toggles and level presets.
  - Verify navigation bounds after filtering (Next disabled when fewer than 5 items remain on last page).

---

## Iteration 2 — Monsters: Quick Filters (client‑side), InlineKeyboard, pagination
Mirror Iteration 1 for monsters, reusing the same approach.

- UI/UX
  - Top row shortcuts:
    - Legendary (toggle)
    - Flying (toggle)
    - CR ranges: 0–3, 4–8, 9+ (mutually exclusive)
    - Size: S, M, L (mutually exclusive)
    - Actions: Apply, Reset
  - List and navigation identical to spells.

- State
  - `context.user_data["monsters_filters"]`:
    - `{ legendary: bool|None, flying: bool|None, cr_range: "0-3"|"4-8"|"9+"|None, size: "S"|"M"|"L"|None, page: int }`.

- Callback data
  - `mflt:leg`, `mflt:fly`
  - `mflt:cr:03` / `mflt:cr:48` / `mflt:cr:9p` / `mflt:cr:clr`
  - `mflt:sz:S|M|L` / `mflt:sz:clr`
  - `mflt:apply`, `mflt:reset`
  - Pagination: `monster:list:page:N` (reused)

- Filtering logic (client‑side)
  - Legendary: `is_legendary == True`.
  - Flying: `is_flying == True`.
  - CR ranges on `cr` value.
  - Size equals shortcut.

- Acceptance criteria and testing
  - Same as Iteration 1, for monsters.

---

## Iteration 3 — Backend: list filtering + pagination parameters
Introduce server‑side filters and pagination for list endpoints to avoid loading entire datasets in the bot.

- Endpoints (non‑breaking; keep existing ones working)
  - Spells: extend `GET /spells` to accept query params:
    - Filters: `level`, `school`, `class` (alias `class`), `ritual`, `is_concentration`, `casting_time`.
    - Pagination: `limit` (default 5), `offset` (default 0).
    - Sorting: optional `order_by` in {`name`, `level`, `-name`, `-level`} (optional in this iteration; can be added in Iteration 5 instead).
  - Monsters: extend `GET /monsters` similarly:
    - Filters: `type`, `size`, `cr_min`, `cr_max`, `is_flying`, `is_legendary`.
    - Pagination: `limit`, `offset`.
    - Sorting: optional `order_by` in {`name`, `cr`, `-name`, `-cr`}.

- Response shape
  - Keep current JSON array response for compatibility.
  - Next‑page detection on the bot: if returned length < `limit` → last page.

- Notes
  - Search endpoints (`/spells/search`, `/monsters/search`) remain unchanged (still `q` required) for name‑contains queries.
  - Indexes: the project already manages performance indexes via Alembic; no ORM metadata changes.

- Acceptance criteria
  - Filtering a list using only `GET /spells` or `GET /monsters` query params works and returns correct subset.
  - Pagination with `limit/offset` works deterministically.

---

## Iteration 4 — Bot: switch lists to server‑side filters/pagination
Replace client‑side filtering/pagination with server calls using the new query params, preserving the same UI/UX.

- Spells
  - Build query string from `spells_filters` and current page (`limit=5`, `offset=(page-1)*5`).
  - Call `GET /spells?...` instead of fetching all.
  - Next button shown only if returned length == `limit`.

- Monsters
  - Same approach using `monsters_filters` and `GET /monsters?...`.

- Callback/state
  - Reuse the same compact callback data and `context.user_data` filter state.

- Acceptance criteria
  - Behavior matches Iterations 1–2 but network usage is reduced; works on large datasets.

---

## Iteration 5 — Sorting toggles (optional if not added in Iteration 3)
Add sorting toggles to the top row, wired to backend `order_by`.

- Spells: Sort: A–Z, Level (↑/↓).
- Monsters: Sort: A–Z, CR (↑/↓).
- Toggle cycles values: e.g., `name → -name → off` if needed.
- Acceptance: list reorders according to selected sort; persists across pagination.

---

## Future (out of scope now)
- Deep links with presets (`t.me/<bot>?start=<key>`), storing preset server‑side by key.
- More granular filters (classes multi‑select, schools, tags) via submenus.
- Result counters and total counts (would require envelope or a separate `count` endpoint).

### Risks & Mitigations
- Callback data length: keep tokens short; store full state in `context.user_data`; callback only signals the mutation.
- Data volume: after Iteration 4, server‑side pagination avoids large payloads.
- Consistency: always edit the same message via `edit_message_text`/`edit_message_reply_markup`.


