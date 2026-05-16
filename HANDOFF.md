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

## 2026-05-16T06:28Z — Codex
**Phase:** Repo bootstrap — GitHub push
**Did:** Added a root `README.md` and committed it. Prepared the repo to push to the GitHub remote provided by the user.
**Next:** Verify the GitHub repo exists and that credentials (SSH key or HTTPS token) are configured if `git push` prompts/fails.
**Handoff to:** Codex — repo-wide git/remote setup per routing table.
**Gotchas:** Repo already had history (`.git` existed); the “first commit” message is just the commit subject, not the repo’s initial commit.

## 2026-05-16T06:47Z — Codex
**Phase:** Local manual test boot
**Did:** Fixed Docker dev boot by switching Compose build contexts to repo-root (so local `agents/` installs), updating `backend/Dockerfile` + `frontend/Dockerfile`, and replacing `curl`-based healthchecks (images lacked `curl`). Added `backend/scripts/seed.py` to generate a demo campaign + leads; stack now boots and API responds.
**Next:** Manual test the UI at `http://localhost:3000` and verify the seeded “Demo Campaign” appears; optionally add real Gmail OAuth keys to test integrations.
**Handoff to:** Claude Code — product polish / UI iteration per routing table.
**Gotchas:** Compose previously marked services unhealthy because `curl` wasn’t present in qdrant/n8n images; healthchecks now use port-level checks.
