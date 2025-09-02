## User Registration & Language Settings Flow

### Goal
Implement a minimal, reliable user registration flow in the Telegram bot and add a user-facing Settings entry to change language preference. Keep existing, battle-tested flows intact; extend without refactoring unrelated code.

### Scope
- Register a user at first interaction ("/start" or any other command/message routed to bot).
- Persist chosen language ("ru"/"en") in the API service DB via `shared_models.User.lang`.
- Add a Settings button to the main menu to change language later.
- Prefer smallest, isolated changes to existing code, avoiding refactors of current handlers.

### Non-Goals
- No full internationalization refactor across all handlers.
- No changes to domain schemas beyond what is already present (`User.lang`).

---

## High-Level Flow

### First interaction
1. User sends `/start` (or any other message/command handled by bot).
2. Bot checks if the user exists in API (by `telegram_id`).
3. If user does not exist:
   - Bot shows a 2-button inline keyboard to choose language: `Русский` / `English`.
   - On choice, bot calls API to create the user with selected language and name from Telegram profile.
   - Bot confirms and shows localized main menu.
4. If user exists:
   - Bot shows localized main menu (without language prompt).

### Change language (Settings)
1. From main menu, user taps `Settings`.
2. Bot shows language selection keyboard (`Русский` / `English`).
3. On choice, bot calls API to update the user’s `lang`.
4. Bot re-renders the main menu in the updated language.

---

## API Requirements

Existing shared model:
- `shared_models.User` with fields: `id`, `telegram_id`, `name`, `is_admin`, `lang` (enum `Language`).

Endpoints (adjust/add minimal set):
- GET user by telegram id (new, minimal):
  - `GET /users/by-telegram/{telegram_id}` → `200` with `User` or `404` if not found.
- Create user (existing path, ensure `lang` is accepted):
  - `POST /users` with body `{telegram_id, name, is_admin=false, lang}` → `201` with `User`.
- Update user language (minimal):
  - `PATCH /users/{user_id}` body `{lang}` → `200` with updated `User`.

Notes:
- If a list/filter endpoint already exists and is simple to extend, `GET /users?telegram_id=...` is acceptable instead of a dedicated by-telegram route. Choose the smallest change that fits current router layout.
- Ensure Alembic state includes `lang` in `user` table (migration appears present). If migrations are incomplete, add a dedicated migration to include `lang` with default `RU`.

---

## Bot Changes (Minimal & Additive)

Files touched (proposed):
- `bot/src/dnd_helper_bot/handlers/menu.py` (add Settings entrypoints and language prompts)
- `bot/src/dnd_helper_bot/main.py` (register new handlers)
- `bot/src/dnd_helper_bot/keyboards/main.py` (extend main menu with Settings)
- `bot/src/dnd_helper_bot/repositories/api_client.py` (add helpers to call new/adjusted user endpoints)

### Registration check
- Implement a tiny helper `ensure_user_registered(update, context)` called at the start of `/start` and in the generic text handler.
  - Retrieve `telegram_id` from `update.effective_user.id`.
  - Call API: `GET /users/by-telegram/{telegram_id}` (or `GET /users?telegram_id=`) to check existence.
  - If 404: show language selection keyboard.
  - Store temporary selection state in `context.user_data["awaiting_lang_choice"] = True` until user clicks.
  - After choice, call `POST /users` with `{telegram_id, name, lang}` and clear the awaiting flag. Cache language in `context.user_data["lang"]`.

### Language selection UI
- Inline keyboard with two buttons: `lang:set:ru` and `lang:set:en`.
- New handler: `CallbackQueryHandler(select_language, pattern=r"^lang:set:(ru|en)$")`.
- On selection:
  - If the user does not exist: create user with this language.
  - If the user exists: update language via API `PATCH /users/{id}`.
  - Update `context.user_data["lang"]` and re-render main menu using selected language.

### Settings menu
- Extend main menu to include `Settings` button with callback `menu:settings`.
- Add handler `CallbackQueryHandler(show_settings, pattern=r"^menu:settings$")` to display language selection UI.

### Language resolution (keep changes minimal)
- Prefer the newly stored `context.user_data["lang"]` for rendering menus where we add code.
- For existing handlers that already compute language using Telegram `language_code`, do not refactor; keep as-is to avoid regressions.
- Over time we can centralize language detection, but out of scope for this task.

---

## Data Validation & Edge Cases
- Multiple rapid clicks on language buttons: guard with a short debounce by ignoring identical repeated selections while a request is in-flight.
- Network/API errors: reply with a concise message and keep the selection keyboard visible so the user can retry.
- Missing `name` from Telegram: fallback to `username` or `"User"`.
- Users changing Telegram client language: do not auto-change stored language; only respect explicit Settings changes.

---

## Testing Plan (inside containers)

Preparation:
- Rebuild/restart services first via the project helper, then run migrations. Wait 5 seconds after restart.
  - `python manage.py restart --build` (preferred wrapper)
  - Wait 5 seconds
  - `python manage.py migrate`

API tests:
- Add/adjust tests for:
  - `GET /users/by-telegram/{telegram_id}` (or filtered list).
  - `POST /users` with `lang`.
  - `PATCH /users/{user_id}` to change `lang`.

Bot manual tests:
1. Start the bot container via the standard compose stack.
2. DM the bot `/start` from a fresh Telegram account:
   - Expect language prompt → choose `English` → user created via API → main menu in English.
3. Tap `Settings` → choose `Русский`:
   - Expect API language update → main menu switches to Russian.
4. Send any other command or text:
   - If registered, no prompt; menu remains localized.

Operational notes:
- Use `docker compose` commands inside the project’s helper if needed, but prefer `manage.py` wrapper where available.

---

## Acceptance Criteria
- First-time user receives a language prompt and gets created in API with chosen `lang`.
- Existing user never sees the prompt again; main menu uses their saved language.
- A visible `Settings` button exists; changing language updates API and UI reflects change immediately.
- All commands executed inside containers; no host-only steps (except poetry lock if ever needed).
- No refactors to unrelated handlers; only additive changes and smallest diffs.

---

## Implementation Checklist (Smallest Possible Changes)
- API: add minimal by-telegram lookup (or filtered list) and `PATCH` for language.
- Bot: add `Settings` button to main menu.
- Bot: add handlers for language selection and settings display.
- Bot: add `ensure_user_registered` used by `/start` and generic text handler.
- Tests: API endpoints; manual bot run-through.

---

## Rollback Plan
- If issues arise, disable the settings handler and language selection callbacks by unregistering them in `main.py`; existing bot flows continue to work with Telegram client locale heuristic.


