## Bot: Search flow should return to Main Menu (not Bestiary/Spells)

### Objective
- Ensure that after showing search results for monsters/spells, the navigation button returns the user to the Main Menu.
- Keep backend unchanged; implement minimal and localized bot-side edits.

### Scope
- Service: `bot`
- No API changes. No database changes.

### Assumptions
- The bot is built with `python-telegram-bot` (>=21) and uses reply keyboards for navigation.
- There is an existing Main Menu keyboard builder/helper function (or it can be introduced with minimal code, reusing existing style and structure).
- Search results are already rendered and sent by the bot, and we only need to adjust the navigation keyboard and its handler.

### UX and Behavior
- When the bot shows search results (monsters or spells), the reply keyboard includes a button labeled "To main menu".
- When the user presses this button, the bot responds with the Main Menu reply keyboard and a short prompt (e.g., "Main menu").

### Implementation Plan
1) Locate current search flow code
   - Find handlers responsible for rendering search results (monsters and spells) in `bot/src/dnd_helper_bot/` (likely in `main.py` or a dedicated handlers module).
   - Identify where the search results keyboard is constructed.

2) Introduce/ensure a main menu keyboard factory
   - If a main menu keyboard builder exists (e.g., `build_main_menu_keyboard()`), reuse it.
   - If it does not exist, add a small helper in the same module (or in an existing keyboards module) to construct the Main Menu reply keyboard, consistent with existing style.

3) Add a "To main menu" button to search results keyboards
   - Update the keyboard used with search results to include a single extra row/button with text: "To main menu".
   - Keep labels consistent with existing language and style.

4) Add a handler for the "To main menu" action
   - Use a text filter for exact match on "To main menu" (or an equivalent constant to avoid typos).
   - Handler action: send a short confirmation message (e.g., "Main menu") and attach the Main Menu reply keyboard.
   - Ensure the handler does not depend on prior state; it should work from any context.

5) Keep changes minimal and localized
   - Do not refactor unrelated handlers or routing.
   - Avoid renaming existing functions unless required.
   - Keep imports and structure consistent with current codebase conventions.

### Testing Plan
- Manual checks (local):
  1. Start services: `docker compose up -d bot redis postgres`.
  2. Interact with the bot: perform a search that yields results.
  3. Verify the reply keyboard includes "To main menu".
  4. Press the button and confirm the Main Menu keyboard appears.
  5. Repeat for both monsters and spells searches.

- Automated tests (if bot tests framework is present):
  - Add/extend a test that simulates pressing the "To main menu" action from a search results context and asserts the outgoing message includes the Main Menu keyboard.

### Rollout
1. Build and restart only the `bot` service to minimize impact:
   - `docker compose build bot`
   - `docker compose up -d bot`
2. Watch logs briefly to confirm no handler errors:
   - `docker compose logs -f bot | cat`

### Edge Cases
- The user presses "To main menu" outside search flow: handler still serves the Main Menu keyboard.
- Rapid presses: idempotent, just re-send Main Menu.
- Localization: if multilingual support exists, ensure the label follows the existing locale strategy.

### Definition of Done
- Search results keyboards for monsters and spells contain a "To main menu" button.
- Pressing the button always shows the Main Menu keyboard.
- No backend or DB changes.
- Changes are minimal and localized to bot UI code.


