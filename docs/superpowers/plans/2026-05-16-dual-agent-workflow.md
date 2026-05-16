# Dual-Agent Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `AGENTS.md` (routing rules) and `HANDOFF.md` (rolling 3-session log) to the repo root, and update `claude.md` to point both agents at them — enabling Claude Code and OpenAI Codex to share state with no re-explanation.

**Architecture:** Pure documentation change. Three files at repo root: one durable rulebook, one rolling log, and a 4-line pointer added to the existing `claude.md`. No code, no hooks, no scripts.

**Tech Stack:** Markdown. Git.

**Spec:** [docs/superpowers/specs/2026-05-16-dual-agent-workflow-design.md](../specs/2026-05-16-dual-agent-workflow-design.md)

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `AGENTS.md` | Create | Durable routing rules, model selection, operational rules, workflow loop. Read at session start by both agents. |
| `HANDOFF.md` | Create | Rolling log of the last 3 sessions. Appended at session end, pruned in the same step. |
| `claude.md` | Modify | Add a "Multi-agent workflow" section pointing Claude Code at `AGENTS.md` + `HANDOFF.md`. |

No other files touched. No tests in the traditional sense — verification is `grep`/file-existence checks.

---

### Task 1: Create `AGENTS.md`

**Files:**
- Create: `AGENTS.md`

- [ ] **Step 1: Write `AGENTS.md`**

Create the file with exactly this content:

````markdown
# AGENTS.md — Dual-Agent Routing Rules

This project is built using **Claude Code** and **OpenAI Codex** together. Both agents read this file at the start of every session.

**Companion file:** [`HANDOFF.md`](HANDOFF.md) — rolling log of the last 3 sessions. Read it after this file.

**Spec:** [`docs/superpowers/specs/2026-05-16-dual-agent-workflow-design.md`](docs/superpowers/specs/2026-05-16-dual-agent-workflow-design.md)

---

## Session start — every session, both agents

1. Read this file (`AGENTS.md`) and `HANDOFF.md`.
2. Announce a routing decision in chat, in one of two forms:
   - "Routing: task class = X → I am the correct agent, proceeding." OR
   - "Routing: task class = Y → switch to {other agent}. Stopping."
3. If Claude Code: also announce the current Claude 5h-window state from the most recent `HANDOFF.md` entry, plus the chosen model.

If the most recent `HANDOFF.md` entry is missing or stale (>24h), say so before proceeding.

---

## Routing rules — task-type first, usage as fallback

### Table A — Which agent

| Task class | Default agent | Why |
|---|---|---|
| Multi-file refactor / repo-wide rename | **Codex** | Heavy context, 1 message |
| Repo-wide review, audit, security sweep | **Codex** | Index whole codebase = 1 message |
| Generating tests across many files | **Codex** | Token-heavy in CC |
| Docs / README updates spanning many files | **Codex** | Same |
| Single-file feature work (e.g. Phase 3B agent) | **Claude Code** | Tight context, deep reasoning |
| Targeted bugfix in 1–2 files | **Claude Code** | Precision over breadth |
| Plan-mode architecture work, spec writing | **Claude Code** | Plan mode is cheap |
| Unit-test authoring for one module | **Claude Code (Haiku)** | Cheap, fast |
| Quick "what does this do" Q&A | **Claude Code** | Codex burns a message |

### Override rule (usage fallback)

If Claude Code has crossed ~80% of its current 5h rolling window (per the last `HANDOFF.md` entry), push **everything** to Codex until the window rolls over — including tasks normally routed to CC.

### Table B — Claude Code model selection

| Task | Model | Command |
|---|---|---|
| Hard architectural reasoning, ambiguous bugs | Opus 4.7 | `/model opus` |
| Default feature building | Sonnet 4.6 | `/model sonnet` |
| Unit tests, formatting, mechanical edits | Haiku 4.5 | `/model haiku` |

---

## Operational rules

- Run `/clear` every ~12 messages, or at the completion of any mini-feature.
- Use plan mode before any non-trivial implementation.
- Disable unused MCP servers — every connected server injects its tool schema into every prompt.
- Never call OpenAI / Anthropic directly from backend code — all LLM calls go through `/agents` (existing project rule).
- One phase per session (existing project rule).

---

## Session end — every session, both agents

1. Append a new entry to `HANDOFF.md` using the template at the top of that file.
2. If `HANDOFF.md` now has more than 3 entries, delete the oldest entry.
3. Commit the `HANDOFF.md` change with message: `chore: handoff log <YYYY-MM-DD> <agent>`.
````

- [ ] **Step 2: Verify the file exists and renders**

Run: `wc -l "AGENTS.md" && head -5 "AGENTS.md"`
Expected: File exists, between 60 and 100 lines, starts with `# AGENTS.md — Dual-Agent Routing Rules`.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs: add AGENTS.md dual-agent routing rules"
```

---

### Task 2: Create `HANDOFF.md` with the first (seed) entry

**Files:**
- Create: `HANDOFF.md`

- [ ] **Step 1: Write `HANDOFF.md` with the seed entry**

The first entry documents the state at the moment this plan was executed — so the very next session has something to read.

Create the file with exactly this content (replace `<UTC-TIMESTAMP>` with the actual current UTC time in `YYYY-MM-DDTHH:MMZ` format when creating the file):

````markdown
# HANDOFF.md — Rolling Session Log

> Last 3 sessions only. Older entries get pruned at the end of each session per `AGENTS.md`.

## Entry template (copy this when appending)

```
## <UTC-TIMESTAMP> — <Claude Code | Codex> (<model if CC>)
**Phase:** <e.g. 3B Personalization Agent>
**Did:** <2–3 sentences max>
**Next:** <what the next session should pick up>
**Claude window:** <approx % used, when it resets>  ← only if Claude Code session
**Handoff to:** <Claude Code | Codex> — <reason from AGENTS.md table>
**Gotchas:** <surprises worth flagging; link to scratchpad.md if longer>
```

---

## 2026-05-16T00:00Z — Claude Code (Opus)
**Phase:** Meta / workflow setup
**Did:** Designed and committed dual-agent workflow spec + plan. Created AGENTS.md and HANDOFF.md at repo root. Updated claude.md with multi-agent pointer.
**Next:** Resume Phase 3B (Personalization Agent). Single-file feature work → Claude Code (Sonnet).
**Claude window:** unknown — first entry. Assume fresh window starting now.
**Handoff to:** Claude Code — Phase 3B is single-file precision work.
**Gotchas:** Codex CLI setup status not verified by this session — confirm `AGENTS.md` is picked up automatically the first time Codex is invoked.
````

- [ ] **Step 2: Verify the file**

Run: `grep -c "^## " "HANDOFF.md"`
Expected: `2` (one template heading + one real entry).

- [ ] **Step 3: Commit**

```bash
git add HANDOFF.md
git commit -m "docs: seed HANDOFF.md with first session entry"
```

---

### Task 3: Update `claude.md` with the multi-agent pointer

**Files:**
- Modify: `claude.md`

- [ ] **Step 1: Read the existing `claude.md`**

Run: `head -20 "claude.md"`
Expected: File starts with `# AI Sales Outreach Automation — Project Context` and a blockquote about Claude Code reading it.

- [ ] **Step 2: Insert the pointer section**

Insert a new section **immediately after** the existing blockquote line (`> Claude Code reads this on every session. Keep it tight; deep details live in /docs.`), before the `## What This Is` heading.

The exact text to insert (with a blank line above and below):

```markdown
## Multi-agent workflow
This project is built using both **Claude Code** and **OpenAI Codex**.
Before any work, read [`AGENTS.md`](AGENTS.md) (routing rules) and [`HANDOFF.md`](HANDOFF.md) (recent session log).
Announce your routing decision before touching code.
Update `HANDOFF.md` at the end of every session — template is at the top of that file.
```

Use the `Edit` tool with:
- `old_string`: the existing blockquote line plus the blank line below it plus the `## What This Is` heading line — match exactly to make the anchor unique.
- `new_string`: the same blockquote line, then the new section, then the `## What This Is` heading.

- [ ] **Step 3: Verify the edit**

Run: `grep -n "Multi-agent workflow" "claude.md"`
Expected: One match, at a line number between 5 and 12.

Run: `grep -n "AGENTS.md" "claude.md"`
Expected: At least one match in the new section.

- [ ] **Step 4: Commit**

```bash
git add claude.md
git commit -m "docs: point claude.md at AGENTS.md and HANDOFF.md"
```

---

### Task 4: Cross-link verification

**Files:**
- Read-only: `AGENTS.md`, `HANDOFF.md`, `claude.md`

- [ ] **Step 1: Confirm every cross-link resolves**

Run each of these and confirm output:

```bash
# claude.md links to AGENTS.md and HANDOFF.md
grep -c "AGENTS.md\|HANDOFF.md" "claude.md"
# Expected: >= 2

# AGENTS.md links back to HANDOFF.md
grep -c "HANDOFF.md" "AGENTS.md"
# Expected: >= 2

# HANDOFF.md references AGENTS.md (in the pruning rule via the template comment)
grep -c "AGENTS.md" "HANDOFF.md"
# Expected: >= 1

# Spec file referenced by AGENTS.md exists
test -f "docs/superpowers/specs/2026-05-16-dual-agent-workflow-design.md" && echo OK
# Expected: OK
```

If any check fails, fix the offending file and re-run. Do not proceed.

- [ ] **Step 2: Final git log check**

Run: `git log --oneline -5`
Expected: Top of the log shows (most recent first) the three commits from Tasks 1–3, on top of the earlier spec commit (`d63567a docs: add dual-agent workflow design ...`).

- [ ] **Step 3: No commit needed**

This task is verification-only. If all checks passed, the workflow is live and the very next session (Claude Code or Codex) will boot into it.

---

## Self-Review

**Spec coverage:**
- File layout (AGENTS.md, HANDOFF.md, claude.md pointer) → Tasks 1, 2, 3
- Routing tables A and B → Task 1
- Override rule (80% window) → Task 1
- Operational rules → Task 1
- Workflow loop (session start / end / template) → Task 1 (start, end, pointer to template) + Task 2 (template lives at top of HANDOFF.md)
- claude.md pointer → Task 3
- "Out of scope" items (no hooks, no script, no per-phase logs) → naturally honored; the plan adds nothing beyond the three files
- Success criteria → exercised by Task 4 cross-link verification

**Placeholder scan:** One templated value — `<UTC-TIMESTAMP>` in Task 2 Step 1 — but it is clearly flagged with instructions ("replace with the actual current UTC time"). No "TBD" / "implement later" / "similar to Task N".

**Type/name consistency:** File names (`AGENTS.md`, `HANDOFF.md`, `claude.md`) match across every reference. Commit message prefixes (`docs:`, `chore:`) are consistent with the project's existing log.
