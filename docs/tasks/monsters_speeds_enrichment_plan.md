## Populate monster speed fields from dnd.su (plan)

### Goal
- Fill `monsters` records in `seed_data_monsters.json` with:
  - `speed_walk` (int, feet)
  - `speed_fly` (int, feet)
  - `speed_climb` (int, feet)
  - `is_flying` (bool)

Notes:
- Only the fields above are in scope. Leave other derived speeds (`speed_swim`, `speed_burrow`) untouched for now.
- If a value cannot be confidently parsed, leave it as `null` and do not invent defaults.

### Inputs / Outputs
- Input seed: `/app/seed_data_monsters.json` (object with keys `monsters`, `monster_translations`).
- Parsed monsters JSON: `/app/scripts/monster_parser/output/parsed_monsters_filtered_final.json` (array or `{ monsters: [...] }`).
- Output seed: `/app/seed_data_monsters_updated.json` (same shape as input seed, with updated `monsters`).

### Reuse existing CLI structure
- Base the new script on `scripts/monster_parser/update_monster_translations.py` CLI and flow:
  - Args: `--seed-in`, `--seed-out`, `--parsed-in`, `--dry-run`.
  - Load seed and parsed data, normalize names, match by slug/name, apply updates, save.

### Matching strategy (same as translations updater)
1. Build `english name by slug` map from `monster_translations` (`lang == 'en'`).
2. For each seed monster, compute a normalized comparison key using:
   - Seed monster slug → english name (fallback), and/or
   - `monster_translations` for `ru`/`en` names.
3. For each parsed monster, normalize `name` and `english_name` fields.
4. Match if normalized names are equal in any of: (seed-ru vs parsed-ru) OR (seed-en vs parsed-en) OR cross-ru/en combinations (identical to the existing updater).

### Parsing speeds from parsed data
- Source field in parsed monster: `speed` (string), e.g. `"30 ft., fly 60 ft. (hover), climb 20 ft."`.
- Extract integers (in feet) for the following tokens:
  - Walk: one of `"speed 30 ft"`, a bare leading number without a keyword, or explicit `"walk 30 ft"`.
  - Fly: token starting with `"fly"`.
  - Climb: token starting with `"climb"`.
- Normalize by:
  - Lowercasing, removing commas and extra spaces.
  - Splitting by `","` or `";"` into segments; evaluate each segment with regexes.
  - Regex examples (non-capturing optional qualifiers):
    - Walk: `^(?:speed|walk)?\s*(\d+)\s*ft` for a segment without other movement keywords.
    - Fly: `^fly\s*(\d+)\s*ft` (ignore `(hover)` and other parentheticals).
    - Climb: `^climb\s*(\d+)\s*ft`.
- `is_flying = True` iff `speed_fly` parsed successfully (> 0). Otherwise `False` if any walk speed exists; leave `null` only if truly unknown.

Edge cases and rules:
- If there is both a leading bare number and an explicit `walk`, prefer explicit; otherwise treat the bare leading number as `walk`.
- Ignore conditional/terrain qualifiers in parentheses; focus on the main numeric value.
- If multiple values appear for the same mode, pick the first numeric one.

### Update targets in seed
- Update only `data['monsters'][i]` fields: `speed_walk`, `speed_fly`, `speed_climb`, `is_flying`.
- Do NOT modify `monster_translations` in this task.

### Script outline (create in `scripts/monster_parser/update_monster_speeds.py`)
1. CLI parsing: `--seed-in`, `--seed-out`, `--parsed-in`, `--dry-run`.
2. Load seed and parsed JSON (support array or `{ monsters: [...] }`).
3. Build helper maps from seed (`slug -> en name`).
4. Iterate seed monsters, find a matching parsed monster by the matching strategy.
5. Parse `speed` string from the parsed monster using robust regexes.
6. Apply updates into the seed monster record.
7. Report per-monster changes (old → new) and counts.
8. If not `--dry-run`, write to `--seed-out` with `ensure_ascii=False, indent=2`.

### Containerized execution
Build the image (if not built):
```bash
docker build -f scripts/monster_parser/Dockerfile -t dnd_helper/monster_parser:latest .
```

Run inside the container (paths are repo-mounted to `/app`):
```bash
docker run --rm \
  -v "$PWD":/app \
  -w /app/scripts/monster_parser \
  dnd_helper/monster_parser:latest \
  python3 update_monster_speeds.py \
    --seed-in /app/seed_data_monsters.json \
    --seed-out /app/seed_data_monsters_updated.json \
    --parsed-in /app/scripts/monster_parser/output/parsed_monsters_filtered_final.json
```

Optional dry-run:
```bash
docker run --rm -v "$PWD":/app -w /app/scripts/monster_parser dnd_helper/monster_parser:latest \
  python3 update_monster_speeds.py --seed-in /app/seed_data_monsters.json \
  --seed-out /app/seed_data_monsters_updated.json \
  --parsed-in /app/scripts/monster_parser/output/parsed_monsters_filtered_final.json \
  --dry-run
```

### Validation & QA
- Sanity checks:
  - Ensure JSON shape unchanged except for target fields.
  - Values are integers or `null`; no strings in speed fields.
  - `is_flying == True` only when `speed_fly` is present and > 0.
- Spot-check a sample of 10 monsters against dnd.su pages.
- If a monster had pre-existing speed values, only overwrite when parsed value differs and is confidently extracted; otherwise keep original.

### Rollout steps
1. Implement `update_monster_speeds.py` under `scripts/monster_parser/` using the described structure.
2. Build container and run with `--dry-run` to review diffs on a subset (optionally add a `--limit` flag if helpful for local testing).
3. Run full update to produce `/app/seed_data_monsters_updated.json`.
4. Manually review a small diff; then replace `seed_data_monsters.json` with the updated file in a separate commit.

### Acceptance criteria
- `seed_data_monsters.json` has `speed_walk`, `speed_fly`, `speed_climb`, `is_flying` populated for monsters where data is available on dnd.su.
- No other unrelated fields changed.
- Script is repeatable and runnable via the provided Docker image, mirroring the existing translations updater CLI.

### Out of scope (for this task)
- Populating `speed_swim` and `speed_burrow`.
- Any DB migrations or API changes.


