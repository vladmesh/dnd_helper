## Handlers and i18n Refactoring Plan

### Context Snapshot (as-is)
- Bot handlers are split into packages:
  - `handlers/monsters/`: filters, render, handlers, lang; `monsters.py` re-exports
  - `handlers/spells/`: filters, render, handlers, lang; `spells.py` contains legacy mixed logic and re-export shim
  - `handlers/menu/`: start/menus/settings/i18n; `menu.py` re-export shim
- API routers are split into packages with consistent structure:
  - `routers/monsters/` and `routers/spells/` expose: endpoints_list/detail/search/mutations, `translations.py`, `derived.py`
  - Provide both raw lists and wrapped (entity + translation + labels) endpoints
- Seeding CLI posts raw entities (POST) and upserts enum/ui translations; bot uses wrapped endpoints

### Observed Issues
- Legacy i18n logic kept alongside new split structure (e.g., `bot/handlers/spells.py` contains duplicated implementations and re-export shim)
- Mixed naming for wrapped endpoints (`/monsters/wrapped-list` vs `/spells/wrapped`) and labeled variants (`/spells/labeled`)
- UI labels in bot are partly hardcoded (e.g., main menu buttons) instead of fully resolved via `/i18n/ui`
- Translation application differs between raw and wrapped list handlers; bulk mutation vs effective dict payloads
- Re-export shims (`monsters.py`, `spells.py`, `menu.py`) still present; some contain logic and can mislead

### Decisions
- Keep both raw and wrapped endpoints in API to support bot and future admin UI.
- Standardize wrapped endpoint naming to `/wrapped` and `/wrapped-list` per domain, maintaining existing for compatibility.
- Centralize i18n selection: API continues to accept `?lang=` and set `Content-Language`. Bot resolves user language uniformly via `handlers/*/lang.py` (already in place).
- For bot, prefer wrapped endpoints exclusively for list/detail/random flows. Avoid applying translations client-side.
- Sunset legacy mixed implementation files; keep only thin re-export shims for backward compatibility, without logic.

### What to Keep
- API `routers/*/translations.py` with current logic for effective translation dicts and bulk application.
- API wrapped list/detail endpoints and enum label resolution.
- Bot packages structure: `handlers/monsters/*`, `handlers/spells/*`, `handlers/menu/*` with split `filters/render/handlers/lang`.
- Re-export shims `handlers/monsters.py`, `handlers/menu.py` as thin shims (no logic) for import stability.

### What to Remove or Move
- Bot `handlers/spells.py`: remove duplicated logic and keep only re-export shim mirroring `handlers/monsters.py`.
- Any hardcoded UI strings in `handlers/menu/i18n.py` and `handlers/menu/settings.py` to be moved to server-side `/i18n/ui` usage gradually (non-breaking).
- Deprecated helper variants inside `bot/handlers/spells.py` (e.g., `_render_spells_list`, `_detect_lang`, `_build_filters_keyboard`) — already reimplemented in `handlers/spells/`.

### Systematization Proposal
- API layer:
  - Monsters: keep `GET /monsters`, `GET /monsters/wrapped-list`, `GET /monsters/{id}/wrapped`.
  - Spells: keep `GET /spells`, `GET /spells/wrapped`, `GET /spells/{id}/wrapped`; keep `GET /spells/labeled` for admin/testing only.
  - Ensure all wrapped endpoints set `Content-Language` and include `labels` consistently.
- Bot layer:
  - Monsters: keep flows implemented in `handlers/monsters/handlers.py` + `render.py` using `/monsters/wrapped-list` and `/{id}/wrapped`.
  - Spells: mirror monsters; ensure usage only of `handlers/spells/*` modules.
  - Menu: keep `menu/__init__.py`, `menus.py`, `settings.py`, `i18n.py`. Replace hardcoded labels with `t()` lookups where feasible.
- Seeding:
  - No change to POST strategy. Continue uploading raw entities and separate translations.

### Cleanup Steps (incremental, minimal changes)
1) Spells handler shim cleanup
   - Replace content of `bot/src/dnd_helper_bot/handlers/spells.py` with a pure re-export (no logic), mirroring `monsters.py`.
   - Verify imports in bot still resolve to `handlers/spells/*` implementations.

2) Align wrapped endpoint naming (optional, non-breaking)
   - Add alias route `GET /spells/wrapped-list` pointing to the same handler as `/spells/wrapped`.
   - Keep existing routes; mark `/spells/labeled` as internal in docs only.

3) Menu i18n tightening (gradual)
   - Replace hardcoded button texts in `menu/i18n.py` and `menu/settings.py` with `t()` calls for keys present in `/i18n/ui` (e.g., `menu.main.title`, `nav.*`).
   - If a key is missing, pass fallback `default=` as now to avoid breaking UX.

4) Documentation update
   - Record the handler conventions (raw vs wrapped) and i18n policy in `docs/architecture.md` (separate PR).

### Acceptance Criteria
- Bot uses only wrapped endpoints in monsters/spells flows.
- `handlers/spells.py` becomes a simple shim, zero duplicate logic.
- No change in public API behavior; legacy routes preserved.
- Minimal code churn; tests stay green.
