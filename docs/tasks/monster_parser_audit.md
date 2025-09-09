## Monster Parser Subproject Audit

### Scope
Audit of the scripts under `scripts/monster_parser` that scrape `dnd.su` and enrich `seed_data_monsters.json` (fill Russian `monster_translations.description`, replace English names with Russian where applicable, and optionally add other fields obtainable from the site).

### Critical Breakages
- Missing module import: `dnd_su_parser_v3.py` imports `git_operations.GitOperations`, but `scripts/monster_parser/git_operations.py` is absent. Any workflow relying on it will fail with ImportError.
- Hardcoded absolute paths (`/home/ubuntu/...`) across multiple scripts (`complete_workflow.py`, `update_monster_translations.py`, `update_monsters_json.py`, `filtered_mass_parser.py`, `analyze_sources.py`, `dnd_su_parser_v3.py`). This breaks portability, contradicts our container-only execution policy, and couples scripts to a specific host.
- Data format mismatch in `update_monsters_json.py`: it assumes the seed file is a list, while the actual file is a JSON object with keys `monsters` and `monster_translations`. Logic based on direct list iteration and `.get()` on monster dicts will not work as intended.
- Inconsistent output filenames across scripts:
  - `filtered_mass_parser.py` writes `parsed_monsters_filtered_batch_*.json` and `parsed_monsters_filtered_final.json`.
  - `complete_workflow.py` and `update_monsters_json.py` expect `parsed_monsters_final.json` (no `filtered_`).
  - `analyze_sources.py` looks for `parsed_monsters_batch_*.json` (no `filtered_`).
  This prevents scripts from finding each other's outputs.
- `complete_workflow.py` depends on the missing `git_operations` and the broken `MonsterDataUpdater` usage, so it is not runnable.

### Duplications and Logic Issues
- Two competing update strategies:
  - `update_monster_translations.py` correctly targets `monster_translations` (fills empty Russian `description`, replaces English `name` with Russian when appropriate) by matching normalized names.
  - `update_monsters_json.py` attempts to update core monster fields, but is built against the wrong seed format and duplicates parts of the matching/normalization logic. Result: overlapping purpose and inconsistent behavior.
- Name normalization and English-text detection are implemented in multiple files with slightly different rules, leading to inconsistent matching and updates.
- Source filtering/analysis is split between `analyze_sources.py` and `filtered_mass_parser.py` but they operate on different filename conventions.

### README Inaccuracies and Gaps (`scripts/monster_parser/README.md`)
- References `git_operations.py`, which no longer exists.
- Suggests running outside containers and relies on absolute paths; violates project policy to run processes inside containers.
- States Python 3.7+, while the repo standardizes on Python 3.11.
- Claims parser extracts `size`/`type`, but the current implementation populates a combined `size_and_type` string; documentation does not reflect actual fields.

### Data and Parsing Coverage
- Link discovery in `filtered_mass_parser.py` scrapes only the main `/bestiary/` page without explicit pagination handling. Likely misses a substantial portion of monsters.
- Field extraction uses brittle text/HTML patterns (expected for scraping), but README overpromises stability of extracted fields relative to the code.
- Data quality summaries exist but are not integrated into a coherent, parameterized workflow; they also depend on hardcoded, host-specific paths.

### Remove (or Freeze) Pending Rework
- Remove unused/breaking imports in `dnd_su_parser_v3.py`:
  - `from update_monsters_json import MonsterDataUpdater`
  - `from git_operations import GitOperations`
- Remove or archive until fixed:
  - `update_monsters_json.py` (relies on wrong seed format and duplicates logic already served better by `update_monster_translations.py`).
  - `complete_workflow.py` (depends on missing module and mismatched filenames; not runnable as-is).
- Either remove or align `analyze_sources.py` with the actual output filenames (currently it expects non-existent names).

### Amend / Add
- Parameterize all file paths via CLI arguments (with sane defaults inside the repo, e.g., `scripts/monster_parser/output/...`). Eliminate absolute host paths.
- Enforce containerized execution in docs and examples. Provide a documented `docker compose` command (or `manage.py` wrapper) to run parsing and updating inside the containers.
- Consolidate on a single updater for `monster_translations`:
  - Keep and extend `update_monster_translations.py` to fill Russian `description`, replace English `name` with Russian where appropriate, and optionally add `english_name` when missing.
- Standardize output filenames from the parser and make them the inputs for the updater. For example, have `filtered_mass_parser.py` produce a single `parsed_monsters_filtered_final.json` and have `update_monster_translations.py` consume that path by default.
- Add pagination to link discovery in `filtered_mass_parser.py` to ensure wide coverage of bestiary pages.
- Update README:
  - English language, Python 3.11, containerized execution flow.
  - Reflect actual extracted fields (e.g., `size_and_type`), and the minimal viable workflow: parse → update `monster_translations` → write updated seed JSON under a repo path.
  - Document CLI arguments and default repo-relative paths.
- Extract shared normalization/matching utilities into a small helper module within `scripts/monster_parser` and import it in both the parser and the updater to avoid divergence.

### Minimal Next Steps (suggested)
1) Remove broken imports and archive/remove `update_monsters_json.py` and `complete_workflow.py`.
2) Parameterize paths in `filtered_mass_parser.py`, `update_monster_translations.py`, `check_translation_quality_v2.py`, and `analyze_sources.py`; align file naming.
3) Update README to the current reality and container-based usage; document the one true workflow.
4) Add pagination in the mass parser and rerun a small test batch to validate coverage and updater behavior.


