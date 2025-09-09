## Standardize bot message structure for Monsters and Spells (RU/EN)

### Goal
Unify the rendering of monster and spell messages across search details, random selection, and list→detail transitions with a consistent structure and bolded labels (text before colon). Replace abbreviated labels with full words and add missing labels to UI translations and seeds.

### Scope
- Bot message texts in:
  - `bot/src/dnd_helper_bot/handlers/monsters/handlers.py` → `monster_detail`, `monster_random`
  - `bot/src/dnd_helper_bot/handlers/spells/handlers.py` → `spell_detail`
- UI translation keys and seeding in `seeding/cli.py` (`_default_ui_pairs`).

### Target structure
- Monsters:
  - Name: [monster name]
  - Description: [monster description]
  - Danger level: [CR label]
  - Hit points: [HP]
  - Armor class: [AC]
- Spells:
  - Name: [spell name]
  - Description: [spell description]
  - Level: [spell level]
  - Classes: [classes]
  - School: [school]

Notes:
- Labels must be bold; the label text is the part before the colon.
- Use HTML parse mode for Telegram messages and escape user-facing values.

### i18n/UI keys
Replace abbreviated RU labels and ensure EN labels are full words. Keep existing keys where possible (minimal changes) and update their texts. Add missing keys.

- Update existing keys (keep key names):
  - `label.cr` → RU: "Уровень опасности", EN: "Challenge Rating"
  - `label.hp` → RU: "Хиты", EN: "Hit Points"
  - `label.ac` → RU: "Класс доспеха", EN: "Armor Class"
- Add generic label keys (used by both monsters and spells):
  - `label.name` → RU: "Название", EN: "Name"
  - `label.description` → RU: "Описание", EN: "Description"
- Add missing spell-specific label:
  - `spells.detail.level` → RU: "Уровень", EN: "Level"

Existing keys already suitable:
- `spells.detail.classes` (RU: "Классы", EN: "Classes")
- `spells.detail.school` (RU: "Школа", EN: "School")

All keys reside under namespace `bot` via the `/i18n/ui?ns=bot` endpoint used by `t(...)`.

### Bot rendering changes
- Switch to HTML parse mode for the affected messages to support bold labels.
- Wrap each label in `<b>...</b>` and append `:` followed by the value.
- Escape dynamic values (names, descriptions, labels) for HTML before interpolation.

Monsters (both `monster_detail` and `monster_random`):
- Render lines in the exact order listed in Target structure.
- Keep the existing random suffix behavior, but append it after the Name line (e.g., `Name: Aragorn (random)`), not inside the description.

Spells (`spell_detail`):
- Render lines in the exact order listed in Target structure.
- Use labels returned from API for classes/school; fall back to codes when labels are absent.

### Seeding updates
- File: `seeding/cli.py`, function `_default_ui_pairs()`:
  - Update texts for `label.cr`, `label.hp`, `label.ac` to full words (RU/EN).
  - Append new pairs for `label.name`, `label.description`, `spells.detail.level` in both RU and EN.
- Apply seeds in containerized environment:
  - `python3 manage.py restart` (wait ~7s after containers are up)
  - `python3 manage.py seed_ui` (or `python3 seed.py --ui` if that is the established entrypoint)

### Acceptance criteria
- RU and EN: for monster detail, random monster, and spell detail, the message shows 5 lines (monsters) or 5 lines (spells) with bold labels and correct values.
- No abbreviated labels ("ОВ", "ОЗ", "КД") remain in these views.
- Labels are sourced from `/i18n/ui` only; no hardcoded UI strings in handlers.
- Search list UIs remain unchanged (only detail/random message bodies are standardized).

### Out of scope / Notes
- API response shape remains unchanged.
- We do not change inline keyboard button texts beyond i18n updates already defined.
- We do not alter other handlers not listed in Scope.

### Test checklist
- RU user:
  - Open monster detail → verify 5 bold-labeled lines in RU with full words.
  - Random monster → same structure; name line contains "(случайно)" suffix.
  - Spell detail → verify 5 bold-labeled lines in RU; Classes and School are labels.
- EN user:
  - Repeat the three cases; Labels are full EN words; fallback works.
- Negative cases:
  - Missing `labels.cr`/`labels.school` → fallback gracefully to codes; labels stay bold.
  - Descriptions containing `<`/`&` are correctly escaped and do not break formatting.

### Minimal edit points (for implementation)
- `bot/src/dnd_helper_bot/handlers/monsters/handlers.py`
  - Adjust string assembly; pass `parse_mode="HTML"` to `edit_message_text`.
- `bot/src/dnd_helper_bot/handlers/spells/handlers.py`
  - Adjust string assembly; pass `parse_mode="HTML"` to `edit_message_text`.
- `seeding/cli.py`
  - Update `_default_ui_pairs()` as described.
