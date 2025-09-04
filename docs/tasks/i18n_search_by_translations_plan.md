## i18n search by translations — implementation plan (Monsters/Spells)

### Context
- After denormalization, base tables `monster` and `spell` no longer store localized names. Names and descriptions live in `monster_translations` and `spell_translations`.
- Current `/monsters/search` and `/spells/search` endpoints early-return because they previously searched by base `name`.
- Requirement: search buttons must perform substring search by name in the selected language only. Example: searching for `fire` should find `firebolt` and `fireball` if, and only if, those names exist in the selected language’s translation table.

### Scope
- Endpoints: `GET /monsters/search`, `GET /spells/search`.
- Matching: case-insensitive substring match on translation `name` in the requested language; no fallback for matching.
- Filters: preserve and combine existing numeric/enum filters from base tables (AND semantics).
- Response: still populate localized fields via existing `_apply_*_translations_bulk` with fallback for display, but filter strictly by the requested language.

### Design
1) Language selection
   - Reuse `_select_language(lang)` to determine the primary language (`ru` | `en`).
   - Do not use fallback language for the matching condition; fallback remains only for display population.

2) Query shape (Spells)
   - Build a subquery `t` over `spell_translations` with conditions:
     - `t.lang == primary_lang`
     - `LOWER(t.name) ILIKE LOWER('%' || :q || '%')` (or `t.name ILIKE :pattern` with pre-lowered `pattern`)
   - Join base `spell` with `t` by `t.spell_id == spell.id`.
   - Add optional filters over base columns (level, school, class, etc.).
   - Select distinct `spell` rows.
   - After fetch, call `_apply_spell_translations_bulk(session, spells, lang)` and set `Content-Language` header.

3) Query shape (Monsters)
   - Same approach using `monster_translations` joined on `monster.id` with `t.lang == primary_lang` and name substring match.
   - Add optional filters (type, size, cr range, flags, roles, environments) over base `monster` columns.
   - Populate localized fields with `_apply_monster_translations_bulk` for the response.

4) Ordering and limits (minimal viable)
   - Start with default ordering by `t.name ASC` and a hard limit if needed (e.g., 100) to keep responses small.
   - Optionally, when pg_trgm is available, order by `similarity(t.name, :q)` DESC to improve perceived quality (out of current scope if not already enabled).

 

### API changes (minimal, additive)
- `api/src/dnd_helper_api/routers/spells.py` — implement translation-based search query under `/spells/search` as described.
- `api/src/dnd_helper_api/routers/monsters.py` — implement translation-based search under `/monsters/search`.
- Preserve existing filters and logging; keep response headers `Content-Language`.
- Important rule: search filter only uses the requested language; no fallback at matching stage.

### Bot impact
- Bot already sends `lang` with search requests (`handlers/search.py`). No bot-side changes required.

### Seeding/data
- Seed data already writes translations. No changes required for this iteration.

### Testing
1) Unit/integration tests for API search (preferred minimal set):
   - Given two spells with translations: `fireball` (en) and its ru translation `файербол`; search `q=fire`, `lang=en` returns `fireball`; `lang=ru` returns empty.
   - Given `firebolt` exists only in `en`, search `q=fire`, `lang=en` matches it; `lang=ru` does not.
   - Given a monster localized only in `ru`, search by `ru` substring returns it; `lang=en` returns empty.
   - Combine with filters (e.g., `level=3`, `is_concentration=false`) and verify AND semantics.

2) Smoke via bot is optional (manual): ensure inline buttons show localized names for the selected language and that search returns non-empty where expected.

### Rollout steps
1) Rebuild/restart containers:
   - `python manage.py restart` (wait ~7s afterward)
2) Smoke test:
   - `curl "http://localhost:8000/spells/search?q=fire&lang=en" | jq .`
   - `curl "http://localhost:8000/monsters/search?q=дра&lang=ru" | jq .`
3) Run tests:
   - `./run_test.sh`

### Acceptance criteria
- Search endpoints return results only when a translation in the requested language exists and its `name` contains the substring (case-insensitive).
- Existing filters still apply and combine with the search term (AND).
- Response `name`/`description` fields are populated, using fallback only for display, not for search matching semantics.

### Risks and mitigations
- Large datasets: initial minimal ordering; add similarity ordering later if needed.
- Locale drift: ensure `_select_language` maps input strings (`ru|en`) consistently; tests cover both languages.


