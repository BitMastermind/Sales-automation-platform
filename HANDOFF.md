# HANDOFF.md — Rolling Session Log

> Last 3 sessions only. Older entries get pruned at the end of each session per `AGENTS.md`.

## Entry template (copy this when appending)

```markdown
<UTC-TIMESTAMP> — <Claude Code | Codex> (<model if CC>)
**Phase:** <e.g. 3B Personalization Agent>
**Did:** <2–3 sentences max>
**Next:** <what the next session should pick up>
**Claude window:** <approx % used, when it resets>  ← only if Claude Code session
**Handoff to:** <Claude Code | Codex> — <reason from AGENTS.md table>
**Gotchas:** <surprises worth flagging; link to scratchpad.md if longer>
```

(Prepend `## ` to the timestamp line when creating a new entry.)

---

## 2026-05-16T06:30Z — Claude Code (Sonnet 4.6)
**Phase:** 3D Follow-up Agent
**Did:** Implemented the LangGraph follow-up agent using strict TDD. Wrote 5 failing tests first, then implemented `agents/prompts/followup_prompts.py`, `agents/followup_agent.py` (2-node conditional graph: select_strategy → generate_followup), `backend/agents_interface/followup.py`, wired `/api/internal/trigger-followup` to the real interface, and added `followup` to the smoke script. All 81 tests pass with zero regressions.
**Next:** Phase 4 — n8n Workflows (launcher, reply monitor, follow-up scheduler). See `docs/05-N8N-WORKFLOWS.md`.
**Claude window:** ~30% used.
**Handoff to:** Claude Code — n8n workflow export/config is a structured task well-suited to CC.
**Gotchas:** Email model uses raw string enum values `"outreach"` / `"followup"` (not a Python Enum class) — interface layer uses string literals. Model ID used: `claude-sonnet-4-6` (latest Sonnet 4.6).

## 2026-05-16T05:54Z — Codex
**Phase:** Phase 5A — Dashboard Layout + Pages
**Did:** Implemented the full Next.js 16 App Router shell + 4 pages (`/dashboard`, `/campaigns`, `/campaigns/[id]`, `/settings`) with TanStack Query, shadcn/ui primitives, Recharts charts (explicit-height containers), and a typed API client that unwraps the `{ data, error, meta }` envelope. Added URL-param-driven lead drawer (`?lead=<id>`) and a small client “island” Gmail status pill in the header. `npm run build` passes with zero TypeScript errors.
**Next:** Run `cd frontend && npm run dev` and complete Phase 5A manual checks (sidebar active state, Gmail pill, dashboard chart height, campaigns → detail nav, lead drawer URL persistence). Then proceed to Phase 5B (campaign creation modal + CSV upload UI).
**Handoff to:** Claude Code — Phase 5B is UI feature building with tight context per routing table.
**Gotchas:** shadcn/ui in this repo is the Base UI variant (no `asChild` on `Button` / `DropdownMenuTrigger`). Recharts logs a width/height warning during static prerender, but renders correctly at runtime due to explicit `h-[320px]` containers.

## 2026-05-16T05:12Z — Codex
**Phase:** Phase 4 — n8n Workflows
**Did:** Generated production-ready n8n workflow exports in `n8n-workflows/` (`campaign_launcher.json`, `gmail_reply_monitor.json`, `followup_scheduler.json`) with credential-by-name references and HTTP error routing to Slack. Added `n8n-workflows/CREDENTIALS.md`, appended `Setup Order` to `n8n-workflows/README.md`, and noted export gotchas in `scratchpad.md`.
**Next:** Run the manual import checks in n8n (Phase 4 verify list) and tweak node parameters if n8n import complains about any schema fields (especially Gmail node field names / simplify output). Then commit the workflow JSON + docs.
**Handoff to:** Claude Code — Phase 5 frontend work is precision feature building per routing table.
**Gotchas:** No-Code constraint means `reply_text` uses Gmail node simplified fields (`textPlain` fallback). Some idempotency keys on schedule-triggered internal GET calls use the execution id (no natural `$json.id` available).
