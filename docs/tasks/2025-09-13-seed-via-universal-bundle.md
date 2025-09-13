## Seed Enums via Universal Bundle — Plan

### Context
Legacy seeding invoked by `manage.py ultimate_restart` relies on old code paths and no longer works. We now have a universal ingest endpoint (see `docs/tasks/2025-09-12-universal-bundle-ingest.md`) and want to: (a) test it end-to-end, and (b) fix seeding so it uses this new endpoint.

### Scope (this task)
- Only enums and their localized labels via `enum_translations` file type.
- Do NOT include monsters or spells data in this iteration (size and complexity deferred).
- Ensure seeding runs automatically as part of `ultimate_restart` and executes inside containers whenever possible.

### Deliverables
- Seed bundle directory with manifest and NDJSON files:
  - `data/seed_bundle/manifest.json`
  - `data/seed_bundle/enum_translations.en.jsonl` (or `.jsonl.gz`)
  - `data/seed_bundle/enum_translations.ru.jsonl` (or `.jsonl.gz`)
- A container-executed seeding script that posts the bundle to `POST /admin/ingest/bundle` and polls job status.
- `manage.py ultimate_restart` updated to execute the new seeding step after Alembic upgrade.
- Minimal docs in this file explaining how to run & verify locally.

---

## Iterations

### Iteration 1 — Seed bundle preparation (data only)
1. Convert existing `seed_data/seed_data_enums.json` into two NDJSON files by language (`en`, `ru`) for the `enum_translations` type.
   - Mapping from legacy structure to ingest model:
     - `enum_type` → `entity`
     - `enum_value` → `code`
     - `lang` → `lang`
     - `label` → `label`
     - Add required `schema_version`: "1.0" to each line
   - Example NDJSON line:
     ```json
     {"schema_version":"1.0","entity":"monster_type","code":"dragon","lang":"ru","label":"Дракон"}
     ```
2. Place output files under `data/seed_bundle/`:
   - `enum_translations.en.jsonl`
   - `enum_translations.ru.jsonl`
   - Optionally gzip both files (`.jsonl.gz`) if size warrants it.
3. Create `manifest.json` with the following fields for each file:
   - `path`, `type = "enum_translations"`, `lang`, `rows`, `sha256`, and `compression` (`none` or `gzip`).
   - `mode = "upsert"` at the manifest level.
   - Use `run_id` equal to a deterministic value for seeding, e.g. `"seed_enums_v1"`.
   - Example manifest (simplified):
     ```json
     {
       "schema_version": "1.0",
       "source": "seed",
       "run_id": "seed_enums_v1",
       "created_at": "2025-09-13T00:00:00Z",
       "mode": "upsert",
       "files": [
         {"path":"enum_translations.en.jsonl","type":"enum_translations","lang":"en","rows":1234,"sha256":"<sha256>","compression":"none"},
         {"path":"enum_translations.ru.jsonl","type":"enum_translations","lang":"ru","rows":1234,"sha256":"<sha256>","compression":"none"}
       ]
     }
     ```
4. Provide a small helper (script or Make target) to compute `rows` and `sha256` for each file and to validate the manifest against the JSON Schema from the universal bundle spec.

### Iteration 2 — Seeder script (containerized)
1. Implement a Python-based seeding script that:
   - Accepts path to `data/seed_bundle/`.
   - Optionally zips the bundle (`bundle.zip`) with `manifest.json` + data files.
   - Sends it to `POST /admin/ingest/bundle` with `Idempotency-Key: seed_enums_v1`.
   - Polls `GET /admin/ingest/jobs/{job_id}` until completion (with timeout), printing per-file counters and failing on errors.
   - Supports `--dry-run` for validation-only.
   - API URL is configurable via env (default `http://api:8000`).
2. Execute the script inside a container:
   - Preferred: run inside the `api` container with `docker compose exec -T api python -m <module>`.
   - Alternative: a minimal one-off Python image mounting the repo to run the script.

### Iteration 3 — Wire into `ultimate_restart`
1. After Alembic `upgrade head` in `manage.py ultimate_restart`, replace the legacy `seed.py --all` with the new containerized seeding call for enums only.
2. Keep a short sleep (7 seconds) before seeding to ensure API readiness.
3. Fail fast if the job ends in `failed` or `partial_failed` state.

### Iteration 4 — E2E verification
1. Run: `python3 manage.py ultimate_restart`.
2. Observe logs of the seeding job summary (created/updated/unchanged/failed per file).
3. Optionally, verify via API wrapped endpoints that enum labels appear in `labels` blocks.
4. Re-run `ultimate_restart` to confirm idempotency (updates should be 0, unchanged should increment accordingly).

### Iteration 5 — Housekeeping
1. Document the developer workflow in this file (commands below) and keep the seed bundle under version control.
2. Defer monsters/spells bundle generation to a separate task.

---

## File Layout
```
data/
  seed_bundle/
    manifest.json
    enum_translations.en.jsonl      # or .jsonl.gz
    enum_translations.ru.jsonl      # or .jsonl.gz
```

## Commands (developer workflow)
- Generate NDJSON files and manifest (helper script TBD):
  - Compute `rows` and `sha256` for each file
  - Validate manifest structure
- Run end-to-end seeding after full restart:
```bash
python3 manage.py ultimate_restart
```

## Notes and Constraints
- Enforce strict enums and fail-fast validation; do not inject defaults for required values.
- Idempotency: use a stable `Idempotency-Key` header; unchanged rows must be counted separately.
- Keep changes minimal and avoid touching unrelated code paths; only wire new seeding where legacy call existed.

## Risks/Edge Cases
- API container may not include `requests`; the seeding script should either use stdlib or rely on available deps.
- If the admin ingest endpoint is not yet available or behind auth, the script must fail clearly with actionable output.
- Large files should be gzipped; for enums, plain `.jsonl` is acceptable.

## Out of Scope
- Seeding of monsters and spells data (to be handled in a separate follow-up task).


