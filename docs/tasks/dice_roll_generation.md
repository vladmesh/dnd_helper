## Simple Dice Rolling in Bot (No API) — Minimal Implementation Plan

### Goal
Let a user input the number of dice and the die faces (nominal) and get the roll results directly in the Telegram bot. No API calls, no cryptographic randomness — standard `random` is enough.

### Scope
- Service: `bot` only.
- No backend (`api`) changes. No DB changes.
- Keep implementation minimal and self-contained.

### UX
- Entry point: add a simple flow in the bot to roll dice.
- Interaction (two-step, simplest):
  1) Bot asks: "How many dice?" (positive integer)
  2) Bot asks: "Die faces?" (e.g., 6 for d6, 20 for d20)
- Bot returns: individual rolls and total, e.g.:
  - "Rolling 3 × d6 → [2, 5, 1], total = 8"

### Validation and Limits
- Count: integer, `1 ≤ count ≤ 100` (configurable constant).
- Faces: integer, allowed set `{2,3,4,6,8,10,12,20,100}` (configurable constant).
- Reject invalid inputs with a short hint; re-prompt the same step.
- If `count` is large (e.g., > 50), optionally truncate the printed list of rolls and still show the total.

### Randomness
- Use Python's `random.randint(1, faces)` for each die.
- No seeding; fresh randomness on each request.

### Implementation Plan (Bot)
1. Handler
   - Use `bot/src/dnd_helper_bot/handlers/dice.py` to implement a small conversation handler (or extend existing one if present) with two steps: ask count → ask faces → compute and reply.
   - Validate inputs at each step; on error, send a concise message and re-ask.
2. Utilities
   - Implement a tiny helper function `roll_dice(count: int, faces: int) -> list[int]` that returns the list of rolls. Keep it pure for easy unit testing.
3. Wiring
   - Add an entry point in the main menu (button or command) to trigger the dice flow. Keep wording short (e.g., "Dice").
4. Output format
   - Reply message example: `Rolling {count} × d{faces} → {rolls_str}, total = {sum(rolls)}`.

### Logging
- Log at `info` when a roll happens with sanitized fields: `count`, `faces`, `sum`, and whether truncation applied. Use existing unified logging.

### Testing Plan
- Unit tests for `roll_dice` (ranges, boundaries, error cases for inputs outside limits).
- A lightweight test for the handler happy-path using the bot's testing utilities (optional, if we already have a pattern for handlers).
- Manual test: run the bot in container, try several inputs (small, large, invalid).

### Out of Scope
- Parsing complex expressions (`2d6+1`, multiple terms, advantage/disadvantage).
- Any API endpoints or shared libraries.

### Rollout Steps
1. Implement the handler in `handlers/dice.py` and the helper function.
2. Wire the handler to the main menu/command.
3. Run the bot container and manually verify conversation steps.
4. Add unit tests for `roll_dice`; run tests.
5. Ship.


