## dnd.su Ingestion into MongoDB (raw_monster_dndsu)

### Scope and constraints
- **Source domain**: only `https://dnd.su` (exclude `next.dnd.su`, `multiverse.dnd.su`).
- **Legacy parsers**: keep as reference only; do not extend/modify them.
- **Collection name**: `raw_monster_dndsu`.
- **Infra**: separate lab docker compose (parser + Mongo). No `mongo-express`; use Compass.
- **Process**: run everything inside containers; one command at a time; verify outputs after each step.

### Target data model (v1)
- **Collection**: `raw_monster_dndsu`
- **Indexes**:
  - **unique**: `source.url`
  - **secondary**: `extracted.title.en`, `extracted.title.ru`, `source.page_codes`, `ingest.fetched_at`
- **Document shape**:
  - **source**:
    - `provider`: `"dnd.su"`
    - `url`: string
    - `slug`: string (derived from `/bestiary/<slug>/`)
    - `page_codes`: string[] (e.g., `"MM 14"`, `"MM 24"` when available)
  - **ingest**:
    - `schema_version`: 1
    - `parser_version`: string (tool version)
    - `fetched_at`: ISO datetime string
    - `content_hash`: hash of HTML/text for idempotent upserts
  - **raw**:
    - `html`: full HTML string
    - `text`: plain text (optional)
  - **extracted**:
    - `title`: { `ru`: string, `en`: string|null }
    - `taxonomy`: { `size`: string|null, `type`: string|null, `alignment`: string|null }
    - `ac`: { `value`: int|null, `note`: string|null }
    - `hp`: { `average`: int|null, `formula`: string|null }
    - `speeds`: { `walk`: int|null, `fly`: int|null, `swim`: int|null, `climb`: int|null, `burrow`: int|null, `hover`: bool|null, `raw`: string }
    - `abilities`: { `str`: int|null, `dex`: int|null, `con`: int|null, `int`: int|null, `wis`: int|null, `cha`: int|null }
    - `saving_throws`: [ { `ability`: 'str'|'dex'|'con'|'int'|'wis'|'cha', `bonus`: int } ]
    - `skills`: [ { `name`: string, `bonus`: int } ]
    - `damage`: { `resistances`: string[], `immunities`: string[], `vulnerabilities`: string[] }
    - `condition_immunities`: string[]
    - `senses`: { `blindsight_ft`: int|null, `darkvision_ft`: int|null, `tremorsense_ft`: int|null, `truesight_ft`: int|null, `passive_perception`: int|null, `raw`: string }
    - `languages`: { `items`: string[], `telepathy_ft`: int|null, `raw`: string }
    - `cr`: { `value`: string|number, `xp`: int|null }
    - `proficiency_bonus`: int|null
    - `environment`: string[]
    - `sources`: [ { `code`: string, `page`: int|null } ]
    - `traits`: [ { `name`: string, `text_html`: string, `text_plain`: string } ]
    - `actions`: [ { `name`: string, `text_html`: string, `text_plain`: string } ]
    - `bonus_actions`: [ { `name`: string, `text_html`: string, `text_plain`: string } ]
    - `reactions`: [ { `name`: string, `text_html`: string, `text_plain`: string } ]
    - `legendary_actions`: [ { `name`: string, `text_html`: string, `text_plain`: string } ]
    - `lair_actions`: [ { `name`: string, `text_html`: string, `text_plain`: string } ]
    - `regional_effects`: [ { `name`: string, `text_html`: string, `text_plain`: string } ]
    - `spellcasting`: { `innate`: string[], `prepared`: string[], `raw_blocks`: string[] }
    - `description`: string
  - **labels**: [ `"dndsu_v1"` ]
  - **diagnostics**: { `warnings`: string[], `errors`: string[] }

Principle: when structured parsing is ambiguous, persist the raw block and record a diagnostic warning; never drop information.

### Parser (new tool, not extending legacy)
- **CLI**:
  - `--base-url` (default `https://dnd.su`)
  - `--bestiary-url` (default `https://dnd.su/bestiary/`)
  - `--delay` (seconds; default 0.5–1.0)
  - `--test-limit` (0 = unlimited)
  - `--resume-file` (path to cached URL list)
  - `--mongo-uri`, `--mongo-db`, `--mongo-collection` (default collection: `raw_monster_dndsu`)
  - `--report-out` (write JSON stats)
- **Crawling**:
  - Collect only `dnd.su` links under `/bestiary/` with pagination via the '>' link.
  - Deduplicate URLs. Validate a page as a monster by presence of key stat blocks.
- **Parsing** (DOM-first, regex as fallback):
  - Titles (ru/en) from `h2` (`Ru [En] ...`) and fallback to `<title>`.
  - Taxonomy (size, type, alignment).
  - AC/HP (value + note/formula).
  - Speeds (raw string + parsed walk/fly/swim/climb/burrow/hover).
  - Abilities (STR..CHA ints).
  - Saving throws, skills → structured arrays from pairs like `Dex +8`.
  - Damage (resistances/immunities/vulnerabilities) and `condition_immunities`.
  - Senses (individual ranges + passive perception) and Languages (list + telepathy ft).
  - CR/Xp, proficiency bonus.
  - Sources codes with page numbers when present; Environment (habitat).
  - Traits/actions/bonus/reactions/legendary/lair/regional and spellcasting blocks (store name + HTML + plain text; if hard → store raw blocks).
  - Description: explicit section or a long paragraph fallback.
- **Persistence**:
  - Upsert by `source.url`. Skip update if `content_hash` unchanged.
- **Throttling/resilience**:
  - Delay between requests, basic retries/backoff, resume via `--resume-file`.

### Lab docker compose (separate from production)
- **Services**:
  - `mongo`: `mongo:6`, persistent volume, mapped port for Compass.
  - `monster_parser`: image from `scripts/monster_parser/Dockerfile` extended with `pymongo`; working dir `/app/scripts/monster_parser`.
- **Env**:
  - `MONGO_URI=mongodb://mongo:27017`
  - `MONGO_DB=dnd_helper`
  - `MONGO_COLLECTION=raw_monster_dndsu`
- **Example usage**:
  - `docker compose -f scripts/monster_parser/docker-compose.lab.yml up -d mongo`
  - `docker compose -f scripts/monster_parser/docker-compose.lab.yml run --rm monster_parser python3 parse_all_dndsu.py --test-limit 30 --delay 0.8`
  - `docker compose -f scripts/monster_parser/docker-compose.lab.yml run --rm monster_parser python3 parse_all_dndsu.py --test-limit 0 --delay 0.8`

No `mongo-express` service; connect via Compass to `mongodb://localhost:27017`.

## Iterative plan (each step is testable)

### Iteration 1 — Infra skeleton
- Add lab compose with `mongo` and `monster_parser` services (no app code changes yet).
- Verify: `docker compose up -d mongo`; connect with Compass; DB visible.

### Iteration 2 — Parser scaffold and Mongo connectivity
- New script `parse_all_dndsu.py` with CLI and a `--dry-run`/connectivity check to insert a dummy document.
- Verify: run once; ensure one dummy doc exists in `raw_monster_dndsu`.

### Iteration 3 — Link discovery (bestiary)
- Implement crawler to collect `/bestiary/` URLs with pagination and domain filter (`dnd.su` only). Save cache to `--resume-file`.
- Verify: `--test-limit 50`; show URL count; inspect cached file.

### Iteration 4 — Raw fetch and minimal persist
- For first N URLs, fetch page, store `source`, `ingest`, `raw.html`, `raw.text`; upsert by URL.
- Verify: documents present with raw HTML; check Compass counts match N.

### Iteration 5 — Core stat extraction
- Extract: titles (ru/en), taxonomy, AC, HP, abilities, speeds (raw + parsed), CR, proficiency bonus.
- Print coverage stats to console and write `--report-out` JSON.
- Verify: sample documents show populated core fields; coverage >80% on core.

### Iteration 6 — Advanced stat extraction
- Extract: saving throws, skills, senses, languages, damage and condition immunities.
- Record `diagnostics.warnings` when parsing is ambiguous; keep raw strings.
- Verify: spot-check several complex monsters; coverage stats improve.

### Iteration 7 — Actions and traits blocks
- Parse traits/actions/bonus/reactions/legendary/lair/regional (name + HTML + plain text). Fallback to raw blocks if needed.
- Verify: sample documents contain arrays with items; text renders correctly in plain.

### Iteration 8 — Sources, environment, spellcasting
- Extract `sources` (code + page when present), `environment` (habitat), and `spellcasting` (innate/prepared/raw_blocks).
- Verify: spot-check pages where these exist.

### Iteration 9 — Full run and idempotency
- End-to-end run without `--test-limit`. Add `content_hash` and skip unchanged on reruns.
- Verify: second run performs upserts with ~0 updates when no content changed. Final `--report-out` saved.

### Iteration 10 — Hardening and docs
- Add retries/backoff; improve error reporting; finalize README and usage notes.
- Verify: rerun after transient failures; ensure resume works via `--resume-file`.

## Test playbook (minimal commands per step)
- Start DB: `docker compose -f scripts/monster_parser/docker-compose.lab.yml up -d mongo`
- Dry-run connectivity: `docker compose -f scripts/monster_parser/docker-compose.lab.yml run --rm monster_parser python3 parse_all_dndsu.py --test-limit 0 --delay 0.8 --report-out /app/scripts/monster_parser/output/report.json`
- Small batch: `--test-limit 30`
- Full run: `--test-limit 0`

## Risks and mitigations
- **Markup drift**: prefer DOM selectors; always persist raw blocks and diagnostics.
- **Ban/DoS**: low concurrency, request delay, retries with backoff.
- **Duplicates**: unique by `source.url`; different pages of the same creature are separate docs by design.

## Acceptance criteria
- Lab compose up; Compass can view `dnd_helper` DB.
- Test batch persists raw + extracted core fields; coverage metrics reported.
- Full run completes; `raw.html` present for all docs; `labels` include `dndsu_v1`.
- Rerun is idempotent (no unnecessary updates when content unchanged).
