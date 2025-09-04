## Goal

Add localized "Back" and "Main menu" inline buttons to all bot menus and flows (beyond the dice menu where they already exist), keeping changes minimal and extending existing, proven code.

## Scope

- Service: `bot`
- UI only; no API or DB changes
- Reuse existing i18n keys: `nav.back`, `nav.main`
- Settings screen is out of scope; keep the single arrow-only button as-is

## Current State (inventory)

- Dice flow (`handlers/dice.py`): already has `_nav_row(lang)` using `t("nav.back")` and `t("nav.main")`; appended in all dice screens.
- Monsters:
  - Root keyboard (`keyboards/monsters.py -> build_monsters_root_keyboard(lang)`): no nav row.
  - List view (`handlers/monsters.py -> _render_monsters_list`): has page nav (back/next) only; no main/back row.
  - Detail view (`handlers/monsters.py -> monster_detail`): has "Back to list" only; no main/back row.
- Spells:
  - Root keyboard (`keyboards/spells.py -> build_spells_root_keyboard(lang)`): no nav row.
  - List view (`handlers/spells.py -> _render_spells_list`): has page nav (back/next) only; no main/back row.
  - Detail view (`handlers/spells.py -> spell_detail`): has "Back to list" only; no main/back row.
- Settings (language selection): `_build_language_keyboard(include_back: bool)` shows only a "⬅️" button to main (hardcoded emoji), no localized labels nor "Main menu" alongside it.
- Search results (`handlers/search.py`): appends a literal "Main menu"/"К главному меню" button; should use `t("nav.main")` for consistency.

## Design Principles

- Keep edits minimal; extend without refactoring large surfaces.
- Centralize nav-row construction where it is already implemented (dice) by introducing a small reusable helper in a common place, or replicate a tiny private helper per handler if cross-module imports become awkward.
- Use existing i18n `t()` for labels; avoid hardcoded strings.
- Prefer editing messages (`edit_message_text`) for callback flows to avoid chat clutter, as currently implemented.

## Implementation Plan (minimal edits)

1) Introduce a shared nav-row helper (option A: shared util; option B: local copies)
- Option A (preferred): Create `dnd_helper_bot/utils/nav.py` with:
  - `async def build_nav_row(lang: str) -> list[InlineKeyboardButton]` → returns `[Back, Main]` using `t("nav.back")`, `t("nav.main")` with `callback_data="menu:main"` for both (matches dice behavior today).
- Option B (zero coupling): Add a private `_nav_row(lang)` function to `handlers/monsters.py`, `handlers/spells.py`, and `handlers/menu.py` (settings) mirroring `handlers/dice.py`.

2) Monsters root menu
- File: `handlers/menu.py -> show_bestiarie_menu_from_callback`
  - After building `kb = build_monsters_root_keyboard(lang)`, construct `rows = [*kb.inline_keyboard, await build_nav_row(lang)]` and pass `InlineKeyboardMarkup(rows)` to `edit_message_text`.
- No change to `keyboards/monsters.py` to keep keyboard builder simple and synchronous.

3) Spells root menu
- File: `handlers/menu.py -> show_spells_menu_from_callback`
  - Same approach as monsters root: append `build_nav_row(lang)` to `kb.inline_keyboard`.

4) Monsters list and detail
- File: `handlers/monsters.py`
  - `_render_monsters_list`: after page navigation row append, add bottom nav row where Back leads to monsters submenu (`menu:monsters`) and Main to main menu.
  - `monster_detail`: replace old list-back button; add bottom nav row where Back leads to current list page (`monster:list:page:<current>`), Main to main menu.

5) Spells list and detail
- File: `handlers/spells.py`
  - `_render_spells_list`: after page navigation row append, add bottom nav row where Back leads to spells submenu (`menu:spells`) and Main to main menu.
  - `spell_detail`: replace old list-back button; add bottom nav row where Back leads to current list page (`spell:list:page:<current>`), Main to main menu.

6) Search results
- File: `handlers/search.py`
  - Replace literal "Main menu"/"К главному меню" with `await t("nav.main", lang)`.
  - Optionally, add a back button if the previous context is well-defined; otherwise, keep only "Main menu" as today.

Settings: no changes
- Language selection remains with a single arrow-only button (intentionally unchanged).

## Implementation Iterations (incremental)

Iteration 1 — Monsters list and detail
- Changes:
  - `handlers/monsters.py`: add bottom nav row in `_render_monsters_list` and add bottom nav row below the existing "Back to list" in `monster_detail`.
- Test:
  - Open monsters list, paginate: bottom Back/Main row present; Back returns to Bestiary submenu, Main to main menu.
  - Open a monster detail: bottom Back/Main row present; Back returns to the same list page, Main to main.

Iteration 2 — Spells list and detail
- Changes:
  - `handlers/spells.py`: add bottom nav row in `_render_spells_list` and add bottom nav row below the existing "Back to list" in `spell_detail`.
- Test:
  - Open spells list, paginate: bottom Back/Main row present; Back возвращает в подменю Заклинаний, Main — в главное меню.
  - Open a spell detail: bottom Back/Main row present; Back возвращает на текущую страницу списка, Main — в главное меню.

Iteration 3 — Root menus for monsters and spells
- Changes:
  - `handlers/menu.py`: in `show_bestiarie_menu_from_callback` and `show_spells_menu_from_callback`, append a Back/Main bottom row to the inline keyboards (by rebuilding markup from `kb.inline_keyboard + [nav_row]`).
- Test:
  - Open Bestiary and Spells root menus from main menu; verify the new Back/Main row appears and works.

Iteration 4 — Search results localization
- Changes:
  - `handlers/search.py`: replace hardcoded "Main menu"/"К главному меню" with `t("nav.main")`.
- Test:
  - Trigger search flows and verify the button label is localized via i18n and still routes to `menu:main`.

Iteration 5 — Optional (deferred): nav-row helper centralization
- Changes (optional):
  - Introduce `utils/nav.py` with `build_nav_row(lang)` and replace local helpers.
- Test:
  - Smoke test all flows touched above to ensure keyboards render identically.

## Edge Cases and Notes

- Back is contextual:
  - From list screens: back to the corresponding submenu (`menu:monsters` / `menu:spells`).
  - From detail screens: back to the current list page (`monster:list:page:<n>` / `spell:list:page:<n>`).
  - From submenus: back to main menu (handled in iteration 3).
- Keep per-page nav (back/next) in lists intact; the new nav row is an extra row at the bottom.
- Do not change message texts beyond what is necessary to attach the new keyboard rows.

## Acceptance Criteria

- Every inline screen (root menus, lists, details, dice) has a bottom row with two buttons: localized "Back" and "Main menu"; both navigate to main menu (`menu:main`).
- Settings screen remains unchanged (single arrow-only button).
- Search results use `t("nav.main")` instead of hardcoded labels.
- No regressions in existing pagination or detail navigation.

## Test Plan (inside containers)

Manual checks:

1) Restart stack and wait before requests
- Run the standard restart command for the project and wait ~5 seconds before interacting with services to let them warm up.

2) Telegram manual flows
- `/start` → Main menu appears
- Dice: open → verify bottom row shows Back/Main; roll; verify row persists
- Bestiary root: open → verify bottom row shows Back/Main → Back returns to main
- Monsters list: apply filters; paginate forward/back; ensure Back/Main row present; open detail → verify row present and works
- Spells root/list/detail: same checks as monsters
- Settings: open → verify it still shows a single arrow-only button; change language → main menu uses selected language
- Search (if applicable in current UX): trigger search, verify the trailing Main menu button is localized

3) Quick code sanity checks
- Grep for hardcoded "Main menu"/"Главное меню" occurrences and replace with `t("nav.main")` where appropriate within the touched handlers.

## Rollback

- Revert the added nav-row calls in `handlers/menu.py`, `handlers/monsters.py`, `handlers/spells.py`.
- If a shared helper was introduced, leave it unused or remove the file; no behavioral impact elsewhere.

## Risks & Mitigations

- Minor coupling between keyboard builders and handlers when appending rows: mitigate by consistently rebuilding `InlineKeyboardMarkup` from `inline_keyboard` + new row.
- Potential i18n fetch failures: keep defaults for `t()` where already used; otherwise, rely on existing i18n behavior.


