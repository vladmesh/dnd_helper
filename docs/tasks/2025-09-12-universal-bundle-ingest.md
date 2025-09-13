## Universal Bundle Ingest – Iterative Plan and Spec

### Goal
Introduce a single universal ingest endpoint that accepts a data "bundle" (manifest + NDJSON files), validates using shared models, and performs idempotent upserts/deletions for monsters, spells, and their translations (multi-language). The same validation/service logic must be reusable by admin endpoints and CLI.

### Non-Goals (for this task)
- No UI work beyond the admin HTTP endpoint.
- No changes to existing domain tables beyond what is already defined in shared models.

### High-Level Design
- Delivery artifact: bundle directory or archive (zip/tar.gz) containing a `manifest.json` and one or more NDJSON files (optionally `.gz` compressed).
- Universal endpoint: `POST /admin/ingest/bundle` accepts a bundle, schedules an async job, and returns `job_id`.
- Status endpoint: `GET /admin/ingest/jobs/{job_id}` returns job state, counters, and error summaries.
- Validation: Pydantic ingest models defined close to `shared_models` (strict enums, fail fast for required data; optional data can be empty but never silently defaulted).
- Processing: batch-wise streaming, transaction per batch, idempotent upserts by stable external key, tombstones for deletions, and optional "authoritative snapshot" mode.

---

## Iterations

### Iteration 1 — Spec, Schemas, Endpoint Skeleton
- Author this spec and JSON Schemas for `manifest.json` and each NDJSON file type.
- Add `POST /admin/ingest/bundle` (accepts zip/tar.gz and bare NDJSON for dev convenience). Validate manifest only; return a created job with `job_id` (job executes a no-op).
- Add `GET /admin/ingest/jobs/{job_id}` returning placeholder progress.

### Iteration 2 — Validation and Job Execution
- Implement job runner: unpack archive (if any), hash verify, per-file stream reader (NDJSON with optional gzip), chunking (e.g., 1k records).
- Add ingest models with strict enums sourced from `shared_models`.
- Implement per-record validation and accumulate per-file counters and errors.
- Persist no data yet; return full validation report in job result.

### Iteration 3 — Upserts for Base Entities
- Implement idempotent upsert for base entities (monsters, spells) by stable `uid`.
- Transaction per chunk; partial failures roll back the current chunk only.
- Metrics: created/updated/unchanged/failed per file.

### Iteration 4 — Translations and Enums
- Implement translations upsert by `(uid, lang)`.
- Implement enum labels upsert by `(entity, code, lang)`.
- Add tombstones support and authoritative snapshot mode per file.

### Iteration 5 — Operational Hardening
- Idempotency-Key header support (falls back to `run_id` from manifest).
- Dry-run mode (`?dry_run=1`) to validate without writes.
- Error artifacts: store line-level error reports; expose retrieval via job endpoint.
- AuthZ: admin-only; rate-limits; input size caps.

---

## Bundle Structure

```
bundle/
  manifest.json
  monsters.jsonl.gz
  monster_translations.en.jsonl.gz
  monster_translations.ru.jsonl.gz
  spells.jsonl.gz
  spell_translations.en.jsonl.gz
  enum_translations.en.jsonl.gz
```

- NDJSON files use UTF-8; one valid JSON object per line; optional gzip compression (`*.jsonl.gz`).
- Filenames are informative; actual semantics come from `manifest.files[].type` and `lang`.

---

## Manifest Specification

### Fields
- `schema_version` (string, required): Manifest schema version (e.g., "1.0").
- `source` (string, required): Origin identifier (e.g., `scraper_v2`).
- `run_id` (string, required): Unique identifier for this bundle run; used for idempotency and audit.
- `created_at` (RFC3339 string, required): Creation timestamp.
- `mode` (string, required): `upsert` | `tombstone` | `authoritative_snapshot`.
- `files` (array, required): Entries describing each data file.

### File Entry
- `path` (string, required): Relative path to file in bundle.
- `type` (string, required): One of `monsters`, `monster_translations`, `spells`, `spell_translations`, `enum_translations`.
- `lang` (string, optional): BCP-47 language code for translation files (e.g., `en`, `ru`).
- `rows` (integer, required): Expected line count (for sanity check).
- `sha256` (string, required): Lowercase hex sha256 of the raw file (before decompression check, see below).
- `compression` (string, required): `none` | `gzip`.
- `depends_on` (array of string, optional): Types that must be processed before this file.

### JSON Schema (simplified)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schema/manifest.schema.json",
  "type": "object",
  "required": ["schema_version", "source", "run_id", "created_at", "mode", "files"],
  "properties": {
    "schema_version": {"type": "string"},
    "source": {"type": "string", "minLength": 1},
    "run_id": {"type": "string", "minLength": 1},
    "created_at": {"type": "string", "format": "date-time"},
    "mode": {"type": "string", "enum": ["upsert", "tombstone", "authoritative_snapshot"]},
    "files": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["path", "type", "rows", "sha256", "compression"],
        "properties": {
          "path": {"type": "string"},
          "type": {"type": "string", "enum": [
            "monsters", "monster_translations", "spells", "spell_translations", "enum_translations"
          ]},
          "lang": {"type": "string"},
          "rows": {"type": "integer", "minimum": 0},
          "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
          "compression": {"type": "string", "enum": ["none", "gzip"]},
          "depends_on": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  }
}
```

### Example
```json
{
  "schema_version": "1.0",
  "source": "scraper_v2",
  "run_id": "2025-09-12T10:33:00Z_042",
  "created_at": "2025-09-12T10:33:05Z",
  "mode": "upsert",
  "files": [
    {"path": "monsters.jsonl.gz", "type": "monsters", "compression": "gzip", "rows": 1240, "sha256": "4b0f7c3f...ab9"},
    {"path": "monster_translations.en.jsonl.gz", "type": "monster_translations", "lang": "en", "compression": "gzip", "rows": 1198, "sha256": "a1c2d3e4...9ff", "depends_on": ["monsters"]}
  ]
}
```

---

## NDJSON File Types – Ingest Models and Constraints

All records include `schema_version` (string, required). All strings are UTF-8. Enums must match codes defined in `shared_models` (e.g., `MonsterType`, `MonsterSize`, `Ability`, `DamageType`, `Condition`, `SpellSchool`, etc.). Required values must be present; do not silently default.

### Common Keys
- `uid` (string, required): Stable unique key per entity across runs. Recommended: `"<source>:<external_id>"`.
- `source` (string, optional if encoded in `uid`): Origin system identifier.
- `external_id` (string, optional if encoded in `uid`): Upstream primary key.

### monsters (base entities)
Minimal example:
```json
{"schema_version":"1.0","uid":"sr1:mon-0001","type":"dragon","size":"huge","ability_scores":{"str":22,"dex":10,"con":20,"int":14,"wis":12,"cha":19},"damage_immunities":["fire"],"condition_immunities":[],"movement_modes":["walk"],"speed_walk":40}
```
Notes:
- Validate `ability_scores` keys strictly against `Ability`.
- No derived/legacy fields (e.g., no `languages` on base; textual languages belong to translations).
- Movement fields per current domain conventions.

### monster_translations
```json
{"schema_version":"1.0","uid":"sr1:mon-0001","lang":"en","name":"Ancient Red Dragon","short_desc":"...","languages_text":"Draconic"}
```
- Primary key: `(uid, lang)`.

### spells (base entities)
```json
{"schema_version":"1.0","uid":"sr1:spell-0001","school":"evocation","level":3,"range":"60 feet","ritual":false,"is_concentration":true,"save_ability":"dex"}
```

### spell_translations
```json
{"schema_version":"1.0","uid":"sr1:spell-0001","lang":"ru","name":"Огненный шар","short_desc":"..."}
```

### enum_translations
```json
{"schema_version":"1.0","entity":"monster_type","code":"dragon","lang":"ru","label":"Дракон"}
```
- Primary key: `(entity, code, lang)`.

### tombstones (optional file type when `mode=tombstone`)
```json
{"schema_version":"1.0","entity":"monster","uid":"sr1:mon-0003","deleted_at":"2025-09-12T12:00:00Z","reason":"removed upstream"}
```

---

## HTTP API Specification

### POST /admin/ingest/bundle
- Auth: admin-only.
- Content-Type:
  - `application/zip` or `application/x-tar` (with gzip): archive containing `manifest.json` + files.
  - `application/x-ndjson` (dev-only single-file mode; `type` query param required).
- Headers:
  - `Idempotency-Key` (optional; if absent, use `manifest.run_id`).
- Query params:
  - `dry_run` (bool, optional): validate only.
- Response (201): `{ "job_id": "<uuid>", "status_url": "/admin/ingest/jobs/<uuid>" }`.

### GET /admin/ingest/jobs/{job_id}
- Response (200):
```json
{
  "job_id": "...",
  "state": "queued|running|completed|failed|partial_failed",
  "started_at": "...",
  "finished_at": "...",
  "files": [
    {"path":"monsters.jsonl.gz","type":"monsters","processed":1240,"created":400,"updated":700,"unchanged":120,"failed":20,"errors_url":"/admin/ingest/jobs/<id>/files/0/errors"}
  ],
  "summary": {"created": ..., "updated": ..., "failed": ...},
  "dry_run": false
}
```

---

## Processing Semantics

- Unpack bundle, locate `manifest.json`, validate against JSON Schema.
- Verify presence of all listed files; verify `sha256` for each file.
- Build processing order using `depends_on` (topological if provided).
- Stream-read NDJSON files line-by-line; support gzip.
- Chunking: configurable (e.g., 1000 records); one DB transaction per chunk.
- Validation: Pydantic ingest models referencing `shared_models` enums; fail fast on required fields; collect line-level errors.
- Upsert rules:
  - Base: by `uid`.
  - Translations: by `(uid, lang)`.
  - Enum translations: by `(entity, code, lang)`.
- Deletions:
  - `mode=tombstone`: apply deletions for listed records.
  - `mode=authoritative_snapshot`: missing records relative to authoritative set are deactivated/soft-deleted (scoped per file type).
- Idempotency: repeated runs with same content must be safe; unchanged rows counted separately.

---

## Security and Operations

- AuthZ: restrict to admin roles.
- Input size limits and per-job record caps to prevent abuse.
- Rate limiting or queue depth control.
- Telemetry: counters per type, timings, error classes.
- All execution inside containers; CLI helper may call the same service functions.

---

## Testing Strategy

- Unit tests for validators and per-record normalization.
- Integration tests for endpoint: small bundles, gzip and plain; validation-only and write modes.
- End-to-end tests using test docker compose: import a realistic sample bundle; assert DB diffs and labels.

---

## Appendix — Minimal JSON Schemas for NDJSON Lines (illustrative)

Note: Exact fields must align with `shared_models` domain. Below are simplified line-level schemas for producers.

### monsters.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "uid", "type", "size", "ability_scores"],
  "properties": {
    "schema_version": {"type": "string"},
    "uid": {"type": "string", "minLength": 1},
    "type": {"type": "string"},
    "size": {"type": "string"},
    "ability_scores": {
      "type": "object",
      "additionalProperties": false,
      "required": ["str", "dex", "con", "int", "wis", "cha"],
      "properties": {
        "str": {"type": "integer"},
        "dex": {"type": "integer"},
        "con": {"type": "integer"},
        "int": {"type": "integer"},
        "wis": {"type": "integer"},
        "cha": {"type": "integer"}
      }
    }
  }
}
```

### monster_translations.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "uid", "lang", "name"],
  "properties": {
    "schema_version": {"type": "string"},
    "uid": {"type": "string", "minLength": 1},
    "lang": {"type": "string"},
    "name": {"type": "string"}
  }
}
```

### spells.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "uid", "school", "level", "range"],
  "properties": {
    "schema_version": {"type": "string"},
    "uid": {"type": "string", "minLength": 1},
    "school": {"type": "string"},
    "level": {"type": "integer", "minimum": 0},
    "range": {"type": "string"},
    "ritual": {"type": "boolean"},
    "is_concentration": {"type": "boolean"}
  }
}
```

### spell_translations.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "uid", "lang", "name"],
  "properties": {
    "schema_version": {"type": "string"},
    "uid": {"type": "string", "minLength": 1},
    "lang": {"type": "string"},
    "name": {"type": "string"}
  }
}
```

### enum_translations.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "entity", "code", "lang", "label"],
  "properties": {
    "schema_version": {"type": "string"},
    "entity": {"type": "string"},
    "code": {"type": "string"},
    "lang": {"type": "string"},
    "label": {"type": "string"}
  }
}
```

---

## Producer Guidance
- Prefer one file per language for translations; base entities in separate files.
- Strictly validate enum codes against the published list; unknowns must fail.
- Provide stable `uid` per entity; avoid recycling.
- Include accurate `rows` and `sha256` in the manifest.
- Use gzip for large files.


