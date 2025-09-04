## Bot/API sync for i18n-translated fields (monsters and spells)

### Context
- We moved user-facing text fields (names, descriptions, some labels) into translation tables.
- The bot UI currently reads legacy fields and therefore shows blanks for the fields migrated to translation tables.
- The API already has groundwork for translations (`monster_translations`, `spell_translations`, `enum_translations`). We must ensure all read endpoints expose translated data in a stable shape for the bot.

### Goals
- Bot renders monsters and spells using translated fields for the requested language.
- Bot renders enum labels (size, role, school, class, etc.) using `enum_translations` (no hardcoded user-facing strings in code).
- API endpoints consistently return both canonical codes and localized labels required by the bot.

### Non-goals
- Data preservation/backfill for existing rows is not required (database does not contain valuable data yet).
- Admin UI for managing translations is out of scope.

### Assumptions
- Query parameter `lang` in API defaults to `ru` when omitted and supports `ru|en`.
- Canonical codes for enums in payloads are stable and equal to Python `Enum.value`.

---

## Deliverables
- Updated bot handlers to consume translated fields from API responses.
- Verified API read endpoints for monsters and spells return translated fields and enum labels (either inline or via a dedicated helper endpoint).
- Smoke tests and small unit tests for formatting and language fallback.
- Brief runbook for manual verification.

---

## Iterative plan

### Iteration 1 — Verify/normalize API response shape
1. Endpoints to verify (read paths):
   - `GET /monsters`, `GET /monsters/{id}`
   - `GET /spells`, `GET /spells/{id}`
2. Expected response shape (per entity):
   - Scalar translated fields exposed as primary fields, e.g. `name`, `description` resolved for the requested `lang` with fallback to the other available language.
   - Optional `translations` block for debugging and future UI needs:
     - `translations: { ru: { name, description }, en: { name, description } }` (only present keys that exist).
   - Enum-coded fields returned as canonical codes plus localized labels for the same fields, one of:
     - Inline label fields (recommended): `size_label`, `school_label`, `classes_labels` (parallel to `size`, `school`, `classes`), resolved by `enum_translations` with fallback.
     - Or a compact map: `enum_labels: { (type,value) -> label }` if we want to keep the payload minimal. The bot can then resolve labels client-side. Pick one approach and keep it consistent across endpoints.
3. If anything is missing, adjust API serializers to resolve labels via `utils/enum_labels.resolve_enum_labels(...)` and to attach the `translations` block.
4. Tests (API):
   - For each endpoint, add/adjust tests that assert presence of localized `name`/`description` and enum labels in RU and EN modes with fallback when a pair is missing.

Commands (inside containers):
```bash
docker compose exec api python - <<'PY'
import httpx
for lang in ("ru","en"):
    r = httpx.get("http://localhost:8000/monsters", params={"lang": lang}, timeout=10)
    print(lang, r.status_code, r.json()[:1])  # show first item only
PY
```

### Iteration 2 — Bot: consume translated fields
1. Read paths to update:
   - Monsters list/details: `bot/src/dnd_helper_bot/handlers/monsters.py` (and any other modules using monster names/descriptions/filters).
   - Spells list/details: `bot/.../handlers/spells.py` (or the actual file used in this project; create if split logically).
2. Rendering logic:
   - Use `name` and `description` from the API response (already resolved by `lang`).
   - Render enum labels using either inline `*_label` fields or the `enum_labels` map returned by the API.
   - Do not hardcode user-facing strings for labels/buttons; use UI translations mechanism already present in the project.
3. Language selection:
   - Determine chat language (existing bot setting or default to `ru`).
   - Pass `lang` query parameter to API requests accordingly.
4. Fallback behavior:
   - If label/text for a requested language is absent, use the fallback provided by the API as-is. The bot should not implement additional fallback beyond displaying what API returned.
5. Tests (bot):
   - Unit tests for formatting: ensure correct extraction of `name`, `description`, and labels from a mocked API payload (both RU and EN).
   - Minimal integration smoke: call the API running in compose and verify at least one monster and one spell render with non-empty texts.

### Iteration 3 — Clean-up and consistency
1. Remove/stop using any legacy fields that are no longer populated by the API.
2. Ensure all places that build filter keyboards or detail cards rely on translated labels from API/UI translation tables.
3. Confirm no user-facing strings remain hardcoded in bot logic (button captions and similar must come from UI translations).

### Iteration 4 — Optional enhancements (time-permitting)
- Cache enum labels client-side in the bot for the session to reduce repeated lookups (invalidate on language change).
- Add a light `/health/i18n` endpoint in API that confirms counts for `monster_translations`, `spell_translations`, and `enum_translations` exist for both languages (useful for monitoring).

---

## Backend checklist
- [ ] `GET /monsters` and `GET /monsters/{id}` include:
  - [ ] `name`, `description` resolved by `lang` with fallback
  - [ ] Enum labels or `enum_labels` for all enum-coded fields in the entity
  - [ ] Optional `translations` block for both languages (when present)
- [ ] `GET /spells` and `GET /spells/{id}` include the same contract as above
- [ ] Enum label resolution uses `enum_translations` with fallback to the other language
- [ ] Seed includes sufficient rows for RU and EN

## Bot checklist
- [ ] All API calls pass `lang` parameter based on chat/user settings
- [ ] All renderers use translated `name`/`description`
- [ ] All enum labels come from API/UI translations (no hardcoded labels)
- [ ] Filter keyboards use translated labels
- [ ] RU and EN manual smoke passes

---

## Manual verification (compose)
1. Start/restart services:
```bash
docker compose up -d
# If containers are already running but code changed:
docker compose restart api bot
```
2. Seed data (if applicable to the current iteration):
```bash
docker compose exec api python /app/seed.py  # or the project-provided seed runner
```
3. API smoke:
```bash
docker compose exec api python - <<'PY'
import httpx
for path in ("/monsters","/spells"):
    for lang in ("ru","en"):
        r = httpx.get("http://localhost:8000"+path, params={"lang": lang}, timeout=10)
        assert r.status_code==200, (path, lang, r.status_code)
        body = r.json()
        assert isinstance(body, list) and len(body)>=0
        if body:
            item = body[0]
            assert "name" in item and item["name"]
            # Either inline labels or an enum_labels map must be present for enum-coded fields
PY
```
4. Bot smoke: open the bot, switch languages if supported, ensure lists and details show translated texts and labels.

---

## Rollout and rollback
- Rollout: merge, restart containers, reseed if necessary.
- Rollback: revert bot to the previous commit; API is backward-compatible (canonical codes are unchanged).

## Acceptance criteria
- In RU and EN, monster and spell lists show translated `name` and `description`.
- Enum-based UI labels are localized and non-empty.
- No hardcoded user-facing labels remain in the bot.


