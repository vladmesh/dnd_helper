## Enhanced response logging: count and preview of returned data

### Objective
- Log not only which endpoint was called, but also what was returned:
  - total number of elements for list responses
  - preview of the first 5 elements
  - for previewed elements, include all fields but trim values to 10 characters
- Apply on both services: `api` (FastAPI) and `bot` (HTTP client side).

### Current state (summary)
- Structured logging is already unified in both services via `configure_logging()` with JSON/human formatters.
  - API: `dnd_helper_api/logging_config.py`
  - Bot: `dnd_helper_bot/logging_config.py`
- API has success logs inside routers (e.g. counts) and error middleware for 5xx/unhandled exceptions.
- Bot logs outgoing requests and response status codes in `repositories/api_client.py`.

### Non-goals
- Do not log full payloads for large responses.
- Do not change business logic or response schemas.
- Do not introduce new dependencies.

### Design overview
- Introduce a small, shared approach per service to compute a safe, clipped preview of payloads.
- API: add middleware that logs response summary after handler execution, for 2xx responses only.
- Bot: enhance existing API client logging to include count and preview after parsing JSON.

### Data preview rules
- If payload is a list:
  - `result_count` = `len(payload)`
  - `result_preview` = transformed first up to 5 items
- If payload is a dict/object:
  - `result_count` = 1
  - `result_preview` = single transformed item
- If payload is a scalar (str/number/bool/null):
  - `result_count` = 1
  - `result_preview` = scalar converted to string and trimmed
- Transformation of an item:
  - If mapping-like (e.g., dict or Pydantic/SQLModel): convert to dict and for each field set value = `clip(value)`
  - If sequence-like: summarize via string form and trim
  - `clip(value)`: convert to string, replace newlines with spaces, trim to max 10 chars, append `…` if truncated
- Hard limits:
  - apply trimming at every leaf
  - preview max 5 items; do not expand nested collections beyond converting to string before trimming

### API changes (minimal and additive)
1) Add middleware `ResponsePreviewMiddleware` in `api`:
   - New file: `api/src/dnd_helper_api/middleware/response_preview.py`
   - Implementation outline:
     - Subclass `BaseHTTPMiddleware`
     - On `dispatch`:
       - call next handler and get `response`
       - only process when `200 <= status_code < 300`
       - safely read JSON body:
         - For `JSONResponse`/`UJSONResponse`, access body bytes via `response.body` or re-wrap using a custom body iterator capture
         - Try `json.loads(body)` with exception guard; if parsing fails, skip preview
       - compute `result_count` and `result_preview` using local utility (see below)
       - log at `INFO` with extras: `method`, `path`, `status_code`, `result_count`, `result_preview`
       - return original response unchanged
     - Ensure compatibility with non-JSON or streaming responses by short-circuiting
   - Middleware should be added after error middleware in `main.py`.

2) Add small utility near middleware, e.g. `api/src/dnd_helper_api/utils/log_preview.py` (or as a helper inside middleware module):
   - `def build_preview(payload: Any) -> tuple[int, Any]:` → returns `(result_count, result_preview)` per rules above

3) Wire-up in `api/src/dnd_helper_api/main.py`:
   - `app.add_middleware(ResponsePreviewMiddleware)` after existing `ErrorLoggingMiddleware`
   - No changes to router logic

4) Env flag (optional):
   - `LOG_RESPONSE_PREVIEW=true|false` (default: `true`). Disable preview logging when set to `false`.

### Bot changes (minimal and additive)
1) Enhance `bot/src/dnd_helper_bot/repositories/api_client.py`:
   - After each successful `resp.json()` in `api_get`, `api_get_one`, `api_post`, `api_patch`:
     - compute `(result_count, result_preview)` using a local lightweight helper
     - log at `INFO` with extras: `url`, `status_code`, `result_count`, `result_preview`
   - Add small utility in the same module (or `bot/.../utils/log_preview.py`) mirroring the API helper logic; keep implementation duplicated to avoid new shared packaging for now.

2) Env flag (optional):
   - `LOG_RESPONSE_PREVIEW=true|false` (default: `true`) to toggle on bot side as well.

### Logging shape (examples)
- API list endpoint (200):
  - message: "Response preview"
  - extras: `{method: GET, path: "/spells", status_code: 200, result_count: 243, result_preview: [{"id": "12", "name": "Fireball…", ...}, ... up to 5]}`
- Bot GET list:
  - message: "API GET preview"
  - extras: `{url: "http://api:8000/spells", status_code: 200, result_count: 243, result_preview: [...]}`

### Files to change/create
- API (additive):
  - create: `api/src/dnd_helper_api/middleware/response_preview.py`
  - create (or inline helper): `api/src/dnd_helper_api/utils/log_preview.py`
  - edit: `api/src/dnd_helper_api/main.py` (register middleware only)
- Bot (edit only):
  - edit: `bot/src/dnd_helper_bot/repositories/api_client.py` (compute and log preview after JSON parse)
- No other files changed.

### Pseudocode for preview helper (shared logic)
```python
def clip_value(value: Any, limit: int = 10) -> str:
    s = str(value).replace("\n", " ")
    return s if len(s) <= limit else s[:limit] + "\u2026"

def transform_item(item: Any) -> Any:
    # Dict-like
    if hasattr(item, "model_dump"):
        item = item.model_dump()
    if isinstance(item, dict):
        return {k: clip_value(v) for k, v in item.items()}
    # Sequence-like → summarized as clipped string
    if isinstance(item, (list, tuple, set)):
        return clip_value(item)
    # Scalar
    return clip_value(item)

def build_preview(payload: Any) -> tuple[int, Any]:
    if isinstance(payload, list):
        count = len(payload)
        preview = [transform_item(x) for x in payload[:5]]
        return count, preview
    if isinstance(payload, dict) or hasattr(payload, "model_dump"):
        return 1, transform_item(payload)
    return 1, transform_item(payload)
```

### Acceptance criteria
- API logs contain for successful JSON responses:
  - method, path, status_code
  - `result_count`, `result_preview` per rules
- Bot logs contain for successful API calls:
  - url, status_code
  - `result_count`, `result_preview` per rules
- Trimming is applied to 10 characters on all values in preview.
- Preview includes at most 5 elements for lists.
- Feature is toggleable via `LOG_RESPONSE_PREVIEW=false`.
- No change to response content or performance regressions beyond minimal overhead of preview.

### Testing plan (containers only)
1) Restart containers and wait 5 seconds.
2) Call representative endpoints:
   - API: `/spells`, `/spells/labeled`, `/monsters`, `/i18n/ui?ns=bot`
   - Bot: trigger flows that call the API (e.g., search handlers)
3) Verify logs show count and preview (values trimmed to 10 chars, max 5 items).
4) Toggle `LOG_RESPONSE_PREVIEW=false` and confirm preview logs are absent while other logs remain.

### Risks and mitigations
- Non-JSON or streaming responses: middleware skips preview when body is not JSON; no interference with streaming.
- Large payloads: we only parse the returned JSON (already generated by FastAPI) and preview the first 5 elements.
- Sensitive data: domain currently contains no secrets; if added later, rely on trimming + explicit allowlist if needed.


