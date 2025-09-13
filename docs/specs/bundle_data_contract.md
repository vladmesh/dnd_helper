## Data Bundle Contract (Producer-Facing)

Audience: external data producer service. This document defines the exact data structures to generate for ingestion. It intentionally excludes ingestion endpoints, jobs, tests, or iteration plans.

Scope: a single bundle (archive) containing a manifest and NDJSON data files for entities and translations.

---

### Bundle Layout

Archive format: `.zip` or `.tar.gz`.

Example layout:
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

NDJSON files:
- Encoding: UTF-8
- One valid JSON object per line
- Compression: gzip recommended (extension: `.jsonl.gz`)

---

### Manifest: `manifest.json`

Describes the bundle contents and metadata. All fields are required unless marked optional.

Fields:
- `schema_version` (string): Manifest schema version, e.g., "1.0".
- `source` (string): Producer/system identifier, non-empty.
- `run_id` (string): Unique identifier of this delivery run; used for idempotency/audit.
- `created_at` (string): RFC3339 timestamp.
- `mode` (string): One of `upsert`, `tombstone`, `authoritative_snapshot`.
- `files` (array of file entries): See below.

File entry:
- `path` (string): Relative path within the archive.
- `type` (string): One of `monsters`, `monster_translations`, `spells`, `spell_translations`, `enum_translations`.
- `lang` (string, optional): BCP-47 language code (e.g., `en`, `ru`) for translation files.
- `rows` (integer): Expected number of NDJSON lines (sanity check, may be approximate but should be close).
- `sha256` (string): Lowercase hex sha256 of the raw file bytes inside the archive.
- `compression` (string): `none` or `gzip`.
- `depends_on` (array of string, optional): File types that must be processed earlier.

Minimal JSON Schema (illustrative):
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

Example manifest:
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

### NDJSON Line Schemas

Common invariants for all lines:
- `schema_version` (string) is required (e.g., "1.0").
- Strings must be UTF-8.
- Unknown/extra fields SHOULD NOT be present.

#### Keying and Idempotency
- Base entities use `uid` (string) as the stable external key: recommended format `"<source>:<external_id>"`.
- Translations key: `(uid, lang)`.
- Enum translations key: `(entity, code, lang)`.

#### Enumerations
Codes must match the API’s enum code sets (lowercase strings), including but not limited to:
- Monsters: `monster_type`, `monster_size`, `danger_level` (CR), `damage_type`, `condition`.
- Spells: `spell_school`, `caster_class`.
- Shared: `ability` keys for `ability_scores` (`str`, `dex`, `con`, `int`, `wis`, `cha`).

Producers must validate codes on their side; unknown enum codes are considered invalid.

---

#### monsters.jsonl[.gz]

Required fields:
- `schema_version` (string)
- `uid` (string)
- `type` (string; monster_type code)
- `size` (string; monster_size code)
- `hp` (integer)
- `ac` (integer)
- `ability_scores` (object with required integer keys `str`, `dex`, `con`, `int`, `wis`, `cha`)

Optional fields (selected):
- `slug` (string)
- `alignment` (string)
- `hit_dice` (string)
- `cr` (string; danger_level code)
- `xp` (integer)
- `proficiency_bonus` (integer)
- `saving_throws` (object: ability→int)
- `skills` (object: skill→int)
- `senses` (object: name→int)
- `damage_immunities` | `damage_resistances` | `damage_vulnerabilities` (array of damage_type)
- `condition_immunities` (array of condition)
- `tags` (array of string)
- `slug`, `subtypes`, `environments`, `roles` (arrays of string where applicable)
- Movement and flags (optional): `is_flying` (bool), `speed_walk|fly|swim|climb|burrow` (int)

Example line:
```json
{"schema_version":"1.0","uid":"sr1:mon-0001","slug":"ancient-red-dragon","type":"dragon","size":"huge","hp":546,"ac":22,"ability_scores":{"str":30,"dex":10,"con":29,"int":18,"wis":15,"cha":23},"damage_immunities":["fire"],"speed_walk":40,"speed_fly":80}
```

---

#### monster_translations.<lang>.jsonl[.gz]

Required:
- `schema_version` (string)
- `uid` (string)
- `lang` (string; must equal file’s `<lang>` value)
- `name` (string)

Optional (selected):
- `description` (string)
- `traits`, `actions`, `reactions`, `legendary_actions`, `spellcasting` (free-form blocks)
- `languages_text` (string)

Example:
```json
{"schema_version":"1.0","uid":"sr1:mon-0001","lang":"en","name":"Ancient Red Dragon","languages_text":"Draconic"}
```

---

#### spells.jsonl[.gz]

Required:
- `schema_version` (string)
- `uid` (string)
- `school` (string; spell_school code)
- `level` (integer ≥ 0)
- `range` (string)

Optional (selected):
- `slug` (string)
- `ritual` (boolean)
- `is_concentration` (boolean)
- `save_ability` (string; ability code)
- `classes` (array of caster_class codes)

Example:
```json
{"schema_version":"1.0","uid":"sr1:spell-0001","slug":"fireball","school":"evocation","level":3,"range":"150 feet","ritual":false,"is_concentration":false,"classes":["wizard","sorcerer"]}
```

---

#### spell_translations.<lang>.jsonl[.gz]

Required:
- `schema_version` (string)
- `uid` (string)
- `lang` (string; must equal file’s `<lang>` value)
- `name` (string)

Optional:
- `description` (string)

Example:
```json
{"schema_version":"1.0","uid":"sr1:spell-0001","lang":"ru","name":"Огненный шар","description":"..."}
```

---

#### enum_translations.<lang>.jsonl[.gz]

Required:
- `schema_version` (string)
- `entity` (string; enum family, e.g., `monster_type`, `monster_size`, `ability`, `damage_type`, `condition`, `spell_school`, `caster_class`)
- `code` (string; enum code value)
- `lang` (string; must equal file’s `<lang>` value)
- `label` (string)

Optional:
- `description` (string)
- `synonyms` (array of string)

Example:
```json
{"schema_version":"1.0","entity":"monster_type","code":"dragon","lang":"en","label":"Dragon"}
```

---

### Tombstones (optional; used when `mode = "tombstone"`)

Delete markers for previously delivered entities. Per-line fields:
- `schema_version` (string)
- `entity` (string; one of `monster`, `spell`)
- `uid` (string)
- `deleted_at` (string; RFC3339)
- `reason` (string, optional)

Example:
```json
{"schema_version":"1.0","entity":"monster","uid":"sr1:mon-0003","deleted_at":"2025-09-12T12:00:00Z","reason":"removed upstream"}
```

---

### Conventions and Quality Gates

- All required fields MUST be present. Do not supply implicit defaults for required values.
- Enum codes MUST be valid; reject/omit lines with unknown codes.
- Use lowercase codes for enums and BCP-47 two-letter language codes where applicable (`en`, `ru`).
- `rows` and `sha256` in the manifest SHOULD reflect the actual files.
- Prefer per-language translation files: `monster_translations.en.jsonl.gz`, `...ru.jsonl.gz`, etc.


