# Claude Code — Operating Guide for This Repo

This guide is for *you, the human*, on how to drive Claude Code productively on this project. Pair it with [CLAUDE.md](../CLAUDE.md) (which Claude reads automatically).

## Mental Model
Claude Code is a coding agent in a loop: **read → plan → write → run → fix**. Your job is to give it:
1. A clear **world model** (CLAUDE.md + `/docs`).
2. A **small, unambiguous task** per session.
3. **Constraints** so it doesn't over-engineer.
4. **Verification instructions** so it knows when it's done.

## The Six Habits

### 1. One phase per session
Each phase in [01-PHASES.md](01-PHASES.md) is one session. Don't blend Phase 2 work into a Phase 3 session — context dilutes and quality drops.

### 2. End every prompt with a verification command
```
… implement X. Verify with: `pytest backend/tests/test_x.py -v` — all tests must pass.
```
This forces the model to actually run its work, not just write it.

### 3. Use "Do NOT" liberally
Claude Code tends toward over-engineering. Bound the work:
> Do NOT install new packages. Do NOT modify existing migrations. Do NOT add a service abstraction.

### 4. Reference exact paths and lines
- Bad: "fix the gmail service"
- Good: "edit `backend/services/gmail_service.py:47` — the refresh token isn't being persisted"

### 5. Paste tracebacks verbatim
Never describe an error. Paste it. The model is excellent at reading stack traces.

### 6. Update `CLAUDE.md` after each phase
The **Current Status** block + a one-line note in `scratchpad.md`. The next session opens warm.

## Effective Prompt Skeleton

```
<Context: which file, what it does, what's wrong / what's needed>

<Task: a single, specific outcome>

<Constraints:
- file paths
- frameworks/libs allowed
- explicit "do NOT"s>

<Verification: the exact command to run and the expected output>
```

## When to Reach for Skills
Claude Code has Superpowers skills installed. Useful ones for this repo:
- **brainstorming** — before designing a new agent or feature (run before writing code).
- **test-driven-development** — when implementing any agent or API route.
- **systematic-debugging** — when a test fails or a bug is reported.
- **verification-before-completion** — invoke before marking any phase done.
- **writing-plans** — at the start of a phase to align on the implementation strategy.

## Common Pitfalls (and what they actually mean)

| Symptom | Real problem | Fix |
|--------|--------------|-----|
| "Claude added a service abstraction I didn't ask for" | Prompt didn't say "no abstractions" | Add explicit "Do NOT" |
| "Tests pass but feature is broken" | Phase 6 not run yet | End every prompt with a verification command |
| "Migration drift between sessions" | Edited a generated Alembic file | Always add a new revision instead |
| "Frontend can't reach backend" | CORS / `NEXT_PUBLIC_API_BASE` mismatch | Check both `.env` files |
| "Agent returns garbage JSON" | Forgot `response_format`/tool-use structured output | Add it; assert Pydantic validation in tests |

## Scratchpad
Keep a top-level `scratchpad.md`. Format:
```markdown
## 2026-05-14 — Phase 2A
- Chose `httpx` over `aiohttp` (better timeout API).
- Surprise: SQLAlchemy 2.0 async needs `text()` wrapper for raw SQL in tests.
- Decision: webhook idempotency key is the n8n execution ID.
```
Reference it in any debugging session: "Check `scratchpad.md` from 2026-05-14 — that pattern applies here."

## Final Rule
> If something feels surprising, **write it down**. Future-you (and future-Claude) will thank you.
