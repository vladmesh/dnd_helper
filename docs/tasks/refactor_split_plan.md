## Refactor Plan — Split Large Files into Logical Modules

### Goal
Decompose files over ~200 lines into coherent, focused modules to improve readability, navigation, and maintainability without changing behavior.

### Principles
- Non-functional change only. Keep public behavior, routes, and handler signatures intact.
- Prefer small, incremental edits. Verify after each step.
- Preserve import paths for external code by using packages with `__init__.py` re-exports where needed.
- Documentation in English; commit messages in English; code comments in English.

### Candidates (>200 lines)
- 763: `api/src/dnd_helper_api/routers/monsters.py`
- 735: `api/src/dnd_helper_api/routers/spells.py`
- 393: `seed.py`
- 306: `bot/src/dnd_helper_bot/handlers/spells.py`
- 305: `bot/src/dnd_helper_bot/handlers/monsters.py`
- 217: `bot/src/dnd_helper_bot/handlers/menu.py`
- 210: `shared_models/src/shared_models/enums.py`

---

## API Routers

### `routers/monsters.py` → package `routers/monsters/` — Status: Completed
Export unified `router` from `__init__.py`. Keep all routes and URLs unchanged.

- `routers/monsters/__init__.py`: create `APIRouter`, include routers from submodules, export `router`.
- `routers/monsters/endpoints_list.py`: `list_monsters`, `list_monsters_wrapped`; helpers `_with_labels`, `_labels_for_monster`, `_effective_monster_translation_dict`.
- `routers/monsters/endpoints_detail.py`: `get_monster`, `get_monster_wrapped`.
- `routers/monsters/endpoints_search.py`: `search_monsters`, `search_monsters_wrapped`.
- `routers/monsters/endpoints_mutations.py`: `create_monster`, `update_monster`, `delete_monster`, `MonsterTranslationUpsert`, `upsert_monster_translation`.
- `routers/monsters/translations.py`: `_select_language`, `_fallback_language`, `_apply_monster_translation`, `_apply_monster_translations_bulk`.
- `routers/monsters/derived.py`: `_compute_monster_derived_fields`, `_slugify`.

Notes:
- Keep shared utilities internal to the package; avoid cross-service coupling.
- No change to response models or query parameter names.

### `routers/spells.py` → package `routers/spells/` — Status: Completed
Mirror the `monsters` layout. Export `router` from `__init__.py`.

- `routers/spells/__init__.py`.
- `routers/spells/endpoints_list.py`: `list_spells`, `list_spells_labeled`, `list_spells_wrapped`.
- `routers/spells/endpoints_detail.py`: `get_spell`, `get_spell_wrapped`.
- `routers/spells/endpoints_search.py`: `search_spells`, `search_spells_wrapped`.
- `routers/spells/endpoints_mutations.py`: `create_spell`, `update_spell`, `delete_spell`, `SpellTranslationUpsert`, `upsert_spell_translation`.
- `routers/spells/translations.py`: `_select_language`, `_fallback_language`, `_apply_spell_translation`, `_apply_spell_translations_bulk`, `_effective_spell_translation_dict`.
- `routers/spells/derived.py`: `_compute_spell_derived_fields`, `_slugify`, `_normalize_casting_time`.

---

## Bot Handlers

### `handlers/monsters.py` → package `handlers/monsters/`
Export public handlers from `__init__.py`.

- `handlers/monsters/__init__.py`: export `monsters_list`, `monster_detail`, `monsters_filter_action`, `monster_search_prompt`, `monster_random`.
- `handlers/monsters/filters.py`: `_default_monsters_filters`, `_get_filter_state`, `_set_filter_state`, `_toggle_or_set_filters`, `_filter_monsters`.
- `handlers/monsters/render.py`: `_render_monsters_list`, `_build_filters_keyboard`, converters (`_cr_to_float`, `_size_letter`).
- `handlers/monsters/handlers.py`: `monsters_list`, `monster_detail`, `monster_random`, `monsters_filter_action`, `monster_search_prompt`, `_nav_row`.
- `handlers/monsters/lang.py`: `_resolve_lang_by_user`.
- Optional: `handlers/monsters/api.py` if we want a thin isolation over `api_get`/`api_get_one`.

### `handlers/spells.py` → package `handlers/spells/`
Same pattern as `monsters`.

- `handlers/spells/__init__.py`: export `spells_list`, `spell_detail`, `spells_filter_action`, `spell_search_prompt`, `spell_random`.
- `handlers/spells/filters.py`: `_default_spells_filters`, `_get_filter_state`, `_set_filter_state`, `_toggle_or_set_filters`, `_filter_spells`.
- `handlers/spells/render.py`: `_render_spells_list`, `_build_filters_keyboard`.
- `handlers/spells/handlers.py`: `spells_list`, `spell_detail`, `spell_random`, `spells_filter_action`, `spell_search_prompt`, `_nav_row`.
- `handlers/spells/lang.py`: `_resolve_lang_by_user`.

### `handlers/menu.py` → package `handlers/menu/`
Keep exports stable via `__init__.py`.

- `handlers/menu/__init__.py`: export `start`, `show_bestiarie_menu`, `show_spells_menu`, `show_main_menu_from_callback`, `show_bestiarie_menu_from_callback`, `show_spells_menu_from_callback`, `show_settings_from_callback`, `set_language`.
- `handlers/menu/start.py`: `start`.
- `handlers/menu/menus.py`: `show_bestiarie_menu`, `show_spells_menu` and related callbacks.
- `handlers/menu/settings.py`: `show_settings_from_callback`, `set_language`, `_build_language_keyboard`.
- `handlers/menu/i18n.py`: `_build_main_menu_inline_i18n`, `_resolve_lang_by_user`.

---

## Seeding

### `seed.py` → keep as thin entrypoint; move logic to `seeding/` — Status: Completed

- `seeding/__init__.py`.
- `seeding/http.py`: `run_curl`, `curl_get_json`, `curl_post_json`.
- `seeding/container.py`: `upsert_enum_and_ui_translations_in_container`.
- `seeding/builders.py`: `_slugify`, `_index_translations`, `_collect_monster_translations_for_slug`, `_collect_spell_translations_for_slug`, `build_monster_payloads_from_seed`, `build_spell_payloads_from_seed`, `build_enum_rows_from_seed`, `build_ui_rows_from_seed`.
- `seeding/cli.py`: argument parsing and `main`.
- `seed.py`: `from seeding.cli import main` and `if __name__ == "__main__": raise SystemExit(main())`.

---

## Shared Models

### `shared_models/enums.py` → package `shared_models/enums/` — Status: Completed
Re-export all symbols from `__init__.py` to preserve `from shared_models.enums import ...` imports.

- `shared_models/enums/__init__.py`: re-export public enums from submodules.
- `shared_models/enums/common.py`: `MovementMode`, `Environment`, `Ability`, `DamageType`, `Condition`, `Language`.
- `shared_models/enums/monsters.py`: `DangerLevel`, `MonsterSize`, `MonsterType`, `MonsterRole`.
- `shared_models/enums/spells.py`: `CasterClass`, `SpellSchool`, `SpellComponent`, `Targeting`, `AreaShape`, `CastingTimeNormalized`.

---

## Order of Work (suggested)
1) `shared_models/enums` (low risk, pure re-exports).
2) `seed.py` → `seeding/` (entrypoint stays; logic moves).
3) API routers: `monsters`, then `spells` (mirror structure; verify routes unchanged).
4) Bot handlers: `monsters`, `spells`, then `menu`.

Verify after each step:
- Imports resolve; application builds and starts in containers.
- Endpoint paths, query params, and response models unchanged.
- Bot handlers register and function as before.

### Acceptance (aligns with backlog item 21)
- No single targeted module remains over ~200 lines (reasonable exceptions aside).
- All tests pass; linters/formatters remain green after the split.


