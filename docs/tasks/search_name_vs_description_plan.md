## Search by Name vs Description — Incremental Plan

### Objective
Enable users to choose the search scope for monsters and spells:
- Name-only (default; preserves current behavior)
- Name + Description (optional, opt-in)

### Constraints & Principles
- Backward compatible: no behavior change unless explicitly requested by the client
- Minimal, incremental edits per iteration; avoid refactors
- Follow existing architecture and i18n policies
- API must be explicit; no silent defaults other than the current name-only behavior
- Tests accompany every iteration

### Glossary
- search_scope: enum with values `name` (default) and `name_description`

---

### Iteration 1 — API contract: add search scope (no functional change by default)
- Add optional query parameter `search_scope` to the monsters and spells list/search endpoints used by the bot.
  - Allowed values: `name` (default), `name_description`.
  - Default must be `name` to preserve current behavior when param is omitted.
- Implement backend validation for `search_scope` and plumb the param to the search layer.
- Keep current filtering logic for `name`; add inclusive filtering by description only when `name_description` is selected.
- Update OpenAPI schema (generated) and endpoint docstrings.
- Tests:
  - Unit tests for parameter parsing and validation.
  - Unit/integration tests that verify identical results when `search_scope` is omitted vs set to `name`.

Acceptance criteria:
- OpenAPI shows `search_scope` on relevant endpoints.
- Requests without `search_scope` behave exactly as now.

---

### Iteration 2 — Bot UX: allow users to choose scope
- Add an inline toggle in the search flow UI to switch between `Name` and `Name + Description`.
  - Use existing i18n policy: no hardcoded labels; introduce new i18n keys for the two options.
  - Default selection: `Name`.
- Store the selected `search_scope` in python-telegram-bot user context (no Redis), e.g., `context.user_data["search_scope"]`.
- Send the chosen `search_scope` with every search request to the API.
- Always display the current scope during search: show a small label/badge in the search prompt/results header and keep the toggle visible.
- Tests:
  - Bot handler unit tests for toggle, state persistence in context, and request building.
  - E2E conversation test for both scopes.
  - Tests verifying the scope label is always visible during search interactions.

Acceptance criteria:
- Users can change scope via inline buttons.
- The choice persists during the session (within PTB context) and is sent to the API.
- The current scope is always visible during search messages.

---

<!-- Iteration removed for MVP: Performance guardrails (indexes) -->

### Iteration 4 — UX polish and usability
- Remember last-used scope across sessions (optional; config-driven).
- Indicate current scope in the prompt or via a small label near the search input/buttons.
  - Use i18n keys for any labels/emojis.
- Allow continuing search from results page: user can type a new query while results are shown; the bot must re-run the search with the same `search_scope` and overwrite the current message (edit in place) with new results and the same scope toggle row.
- Tests:
  - Bot tests for last-scope recall and label rendering.
  - E2E test: from results page, send a new query; ensure the message is edited, not a new message.

Acceptance criteria:
- Users see which mode is active and can switch quickly.

---

### Iteration 5 — Documentation and examples
- Update API usage examples to include `search_scope`.
- Update bot operator docs (if any) on how the toggle works.
- Ensure architecture/i18n docs remain consistent.

Acceptance criteria:
- Docs show how to use `search_scope` with curl and bot flows.

---

### Iteration 6 — Telemetry and logging
- Add structured logs for `search_scope` on the API and bot.
- Add metrics: count, latency, and result sizes split by scope.
- Basic alerting for anomalous latency increases in `name_description`.

Acceptance criteria:
- We can observe usage split and latency by scope.

<!-- Iteration removed for MVP: Rollout controls -->

### Out of scope
- Fuzzy matching, typos tolerance, or weighting score tuning.
- Cross-language description search or translation-aware search.
- Refactors unrelated to the feature.

---

### Test Plan (cumulative)
- API
  - Param validation tests for `search_scope`.
  - Functional tests for `name` vs `name_description` queries.
- Bot
  - Handler tests for toggle interactions and state persistence.
  - E2E conversation tests for both modes.

---

### Rollback strategy
- Revert to default `name` behavior by omitting `search_scope` in API clients.
 
