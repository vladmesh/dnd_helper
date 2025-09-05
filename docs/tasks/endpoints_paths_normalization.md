## Endpoint Path Normalization Plan (Static vs Dynamic)

Goal: eliminate reliance on import order by ensuring that static list/search endpoints can never collide with dynamic detail endpoints. Provide clear, future-proof, and self-documenting URL structure across services.

### Principles
- No path should depend on registration order to resolve correctly.
- Static collections (list/search) must live under explicit, non-ambiguous prefixes.
- Detail routes use dynamic identifiers only under their dedicated segment.
- Backward compatibility provided during a migration window.

### Current State (high-level)
- Monsters
  - List (raw): `GET /monsters`
  - Wrapped list: `GET /monsters/wrapped-list`
  - Detail (raw): `GET /monsters/{monster_id}`
  - Detail (wrapped): `GET /monsters/{monster_id}/wrapped`
  - Search: `GET /monsters/search` (+ potential wrapped variant)

- Spells
  - List (raw): `GET /spells`
  - Labeled list: `GET /spells/labeled`
  - Wrapped list: `GET /spells/wrapped` and alias `GET /spells/wrapped-list`
  - Detail (raw): `GET /spells/{spell_id}`
  - Detail (wrapped): `GET /spells/{spell_id}/wrapped`
  - Search: `GET /spells/search` (+ potential wrapped variant)

Problem: static leaf segments like `/wrapped` or `/wrapped-list` live at the same level as `/{id}`. If dynamic routes are registered earlier, static paths can match the dynamic pattern and cause 422s.

### Proposed Design (clean, import-order independent)
Introduce explicit grouping prefixes for collection operations:

- For both `monsters` and `spells`:
  - List endpoints under `/list`:
    - `GET /<entity>/list/raw` (alias for the existing `GET /<entity>`)
    - `GET /<entity>/list/labeled` (alias for existing `/<entity>/labeled`)
    - `GET /<entity>/list/wrapped` (alias for existing `/<entity>/wrapped` and/or `/<entity>/wrapped-list`)
  - Search endpoints under `/search`:
    - `GET /<entity>/search/raw` (alias for existing `/<entity>/search`)
    - `GET /<entity>/search/wrapped` (alias for existing `/<entity>/search-wrapped` if present)
  - Detail endpoints remain as-is:
    - `GET /<entity>/{id}`
    - `GET /<entity>/{id}/wrapped`

Notes:
- Keep legacy endpoints for a deprecation phase, returning the same payloads.
- New structure avoids any overlap with `/{id}` by adding one extra segment for collections.

### Migration Plan (iterative)
1) Add new routes as thin aliases [DONE]
   - Implemented `/<entity>/list/*` and `/<entity>/search/*` as simple wrappers which delegate to current handlers.
   - Legacy routes are preserved; behavior unchanged.

2) Update API tests [DONE]
   - Added coverage for new paths (`/list/*`).
   - Kept existing tests; all passing in CI containers.

3) Update documentation [IN PROGRESS]
   - Updated `docs/architecture.md` to reference `/list/wrapped` as canonical list endpoint.
   - Deprecation marking to be added in next iteration.

4) Update Bot client
   - Switch the bot’s API client to use the new canonical endpoints.
   - Keep resilience: tolerate both during rollout (feature flag optional).

5) Deprecation signaling (non-breaking)
   - For old routes, add `Deprecation: true` response header and a `Link` header with `rel="successor-version"` pointing to the canonical path.
   - Log a structured warning once per route per process start to avoid noise.

6) Remove legacy routes (post deprecation window)
   - After one release cycle with the bot migrated, remove old paths.
   - Remove any per-file Ruff ignores that were added solely due to import ordering.

### Implementation Details
- Routers
  - Define sub-routers: `list_router = APIRouter(prefix="/list")` and `search_router = APIRouter(prefix="/search")` within each domain package.
  - Mount them into the main domain router (`/monsters`, `/spells`).
  - Keep existing function bodies; route handlers can call existing helpers.

- Handlers
  - Prefer reusing current handler functions to avoid duplication (pass through args, return values unchanged).
  - Ensure response models remain identical for old vs new endpoints.

- Logging and headers
  - Preserve current structured logs.
  - For new routes, set `Content-Language` and other headers same as legacy.
  - For old routes, add deprecation headers as described.

- Configuration & Linters
  - No global changes needed to Ruff.
  - If any `__init__.py` depended on import order previously, you can remove per-file ignore `I001` after migration, since path structure no longer collides.

### Backward Compatibility
- Zero breaking changes during the transition; both old and new endpoints coexist.
- Bot migration will be done before retiring legacy paths.

### Risks & Mitigations
- Risk: clients pinned to old paths missing deprecation comms.
  - Mitigate via headers, docs, and logging; maintain aliases for agreed window.
- Risk: test duplication and drift.
  - Mitigate by delegating new routes to the same handlers; keep assertions in one place where possible.

### Acceptance Criteria
- New endpoints exist and return identical payloads to their legacy counterparts.
- API tests pass for both legacy and new endpoints during migration.
- Bot updated to use new endpoints; no user-facing regressions.
- After deprecation window, legacy endpoints removed and tests adjusted; no route relies on registration order.

### Suggested Timeline (incremental)
- Iteration 1: Add aliases + tests + docs updates.
- Iteration 2: Migrate bot client.
- Iteration 3: Enable deprecation headers on legacy endpoints.
- Iteration 4: Remove legacy endpoints and any temporary linter ignores.

---

## Addendum: Remove "labeled" endpoints (keep only raw and wrapped)

Decision: the "labeled" collection endpoints are redundant given the availability of "wrapped" responses (which already provide enum labels) and add ambiguity to the API surface. We will remove them entirely and keep only "raw" and "wrapped".

Scope:
- Spells:
  - Remove `GET /spells/labeled` implementation and references.
  - Remove any aliases under the future `/spells/list/labeled` if introduced during migration.
- Monsters:
  - Do not introduce `GET /monsters/labeled` (if absent) and remove any references in docs.

Migration steps:
1) Deprecation window (short)
   - If `GET /spells/labeled` is currently used internally, add `Deprecation: true` and a `Link` header pointing to the canonical successor: `GET /spells/wrapped` (or `/spells/list/wrapped` after path normalization).
   - Update documentation (architecture and task docs) to state removal and recommend `wrapped`.

2) Code removal
   - Delete the handler for `GET /spells/labeled` and its router hook-up.
   - Remove any tests that target `labeled`; where feasible, replace with equivalent `wrapped` assertions.
   - Search and remove dead imports/usages.

3) Documentation cleanup
   - Update `docs/architecture.md`: remove mentions of `labeled` endpoints; clarify that clients should use `wrapped` for enum labels and localized content, and `raw` for pristine entities.
   - Update task docs referencing `labeled` to either point to `wrapped` or state historical context only.

4) Bot alignment
   - Ensure the bot uses only `wrapped` (for localized UI) or `raw` where appropriate; no calls to `labeled` remain.

Acceptance criteria:
- No remaining routes expose `.../labeled`.
- Tests pass using only `raw` and `wrapped` endpoints.
- Documentation contains no references to `labeled` outside of historical notes.


