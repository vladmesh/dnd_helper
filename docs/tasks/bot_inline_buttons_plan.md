## Goal
Convert the Telegram bot's top-level menu from text-based ReplyKeyboard buttons to inline buttons handled via callback queries, while preserving existing flows for monsters, spells, and dice. Minimize touching proven code: extend with new handlers/builders and wire them in.

## Scope
- Service: `bot`
- No API/database changes
- Keep existing text-based handling (`handle_menu_text`) for backward compatibility

## Current State (as of repo snapshot)
- Main menu is ReplyKeyboard-based: `keyboards/main.py -> build_main_menu()` returns `ReplyKeyboardMarkup` with labels:
  - "Бросить кубики"
  - "Бестиарий"
  - "Заклинания"
- Text routing: `handlers/text_menu.py -> handle_menu_text()` switches by exact text to:
  - `handlers/dice.show_dice_menu`
  - `handlers/menu.show_bestiarie_menu`
  - `handlers/menu.show_spells_menu`
- Submenus already use inline keyboards and callback queries:
  - Monsters: `keyboards/monsters.py`, `handlers/monsters.py` with patterns `^monster:*`
  - Spells: `keyboards/spells.py`, `handlers/spells.py` with patterns `^spell:*`
- There is an existing callback to main menu: `handlers/menu.show_main_menu_from_callback` registered with pattern `^menu:main$`
- Dice flow: has inline keyboard once inside dice, triggered currently from text-based menu

## Design Overview
Introduce an inline main menu (callback-based) without breaking existing text-based flows.

- Callback data convention:
  - `menu:dice` → open dice menu
  - `menu:monsters` → open monsters root inline menu
  - `menu:spells` → open spells root inline menu
  - `menu:main` → show main menu (already used in search results)
- Extend, do not rewrite:
  - Keep `build_main_menu()` and `handle_menu_text()` for typed input/fallback
  - Add new inline builder and callback-aware handlers as wrappers around existing logic

## Implementation Steps
1) Keyboards: add inline main menu builder
- File: `bot/src/dnd_helper_bot/keyboards/main.py`
- Add `build_main_menu_inline() -> InlineKeyboardMarkup`:
  - Rows:
    - [ "Бросить кубики" → `menu:dice` ]
    - [ "Бестиарий" → `menu:monsters`, "Заклинания" → `menu:spells` ]

2) Handlers: add callback-aware wrappers
- File: `bot/src/dnd_helper_bot/handlers/menu.py`
  - Add `show_main_menu_inline(update, context)` to send inline main menu (non-callback entry if needed)
  - Add `show_bestiarie_menu_from_callback(update, context)`:
    - `query = update.callback_query`; `await query.answer()`
    - `await query.edit_message_text("Бестиарий:", reply_markup=build_monsters_root_keyboard())`
  - Add `show_spells_menu_from_callback(update, context)` similarly for spells
  - Update `show_main_menu_from_callback` to use inline main menu builder (not ReplyKeyboard)

- File: `bot/src/dnd_helper_bot/handlers/dice.py`
  - Add `show_dice_menu_from_callback(update, context)`:
    - `query = update.callback_query`; `await query.answer()`
    - `await query.edit_message_text("Бросить кубики:", reply_markup=<existing dice InlineKeyboardMarkup>)`
    - Reuse the same inline keyboard rows as in `show_dice_menu`

3) Wire callback routes
- File: `bot/src/dnd_helper_bot/main.py`
  - Register handlers:
    - `CallbackQueryHandler(show_dice_menu_from_callback, pattern=r"^menu:dice$")`
    - `CallbackQueryHandler(show_bestiarie_menu_from_callback, pattern=r"^menu:monsters$")`
    - `CallbackQueryHandler(show_spells_menu_from_callback, pattern=r"^menu:spells$")`
    - Keep/ensure `CallbackQueryHandler(show_main_menu_from_callback, pattern=r"^menu:main$")`
  - Optional: change `/start` to send the inline main menu instead of ReplyKeyboard

4) Keep text fallback intact (no behavior change)
- Do not remove `ReplyKeyboardMarkup` `build_main_menu()`
- Do not modify `handlers/text_menu.py` logic; it will still work for typed text

## Minimal Code Touch Points
- `keyboards/main.py`: add new function only
- `handlers/menu.py`: add two new callback functions; adjust `show_main_menu_from_callback` to inline builder
- `handlers/dice.py`: add one callback wrapper function; reuse existing inline keyboard definition
- `main.py`: add three `CallbackQueryHandler` registrations

## Logging
- Follow existing logging pattern (`logger.info` with `correlation_id`, `user_id`, and relevant fields)
- For each new handler, log an entry at INFO level when invoked

## Testing Plan
- Unit-level checks (lightweight):
  - Build inline main menu returns `InlineKeyboardMarkup` with 3 buttons and expected `callback_data`
- Manual E2E checks (in container):
  1. Restart stack and wait 5 seconds
  2. Open chat, run `/start` → inline main menu is shown
  3. Tap "Бросить кубики" → dice inline menu appears; tap several dice options → results arrive; tap back to main via a `menu:main` button if present
  4. Tap "Бестиарий" → monsters root inline menu; navigate list/detail and back
  5. Tap "Заклинания" → spells root inline menu; navigate list/detail and back
  6. Type plain text "Бестиарий" → still works via text handler
- Regression checks:
  - Search flows still use `menu:main` and are unaffected
  - Existing callback patterns for `monster:*`, `spell:*`, and `dice:*` remain functional

## Risks & Mitigations
- Mixed menus (reply vs inline): ensure `/start` shows inline; keep reply keyboard only for typed fallback
- Message editing vs replying: prefer `edit_message_text` from callbacks to reduce clutter
- Callback pattern collisions: patterns are distinct (`menu:*` vs existing namespaces)

## Rollback Plan
- In `main.py`, remove new `CallbackQueryHandler`s for `menu:(dice|monsters|spells)` and point `/start` back to `build_main_menu()`
- Keep new functions in place (no functional impact if unused)

## Acceptance Criteria
- `/start` shows inline main menu with three options
- Tapping any option triggers the correct flow via callback (no text parsing)
- Text commands (typing "Бестиарий"/"Заклинания"/"Бросить кубики") still function
- No changes required on API or shared models
