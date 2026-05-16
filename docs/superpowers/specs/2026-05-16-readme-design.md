# README Design Spec — 2026-05-16

## Summary

A single `README.md` at the repo root that reads like a startup pitch deck — bold, narrative-first, designed to impress hiring managers, collaborators, and technical stakeholders. Uses Mermaid diagrams (renders natively on GitHub). Non-tech readers get the value prop in the first screen; engineers get architecture depth below.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Tone | Startup Landing Page | Bold headline, value prop up front, non-tech accessible |
| Primary goal | Portfolio / impress | Showcases system depth — not a quickstart-first doc |
| Diagrams | Mermaid | Renders as vector graphics on GitHub; clean and professional |
| Structure | Pitch Deck Narrative | Problem → Solution → Flow → Architecture → Stack → Status → Quickstart |

---

## Section-by-Section Spec

### 1. Hero

- **Product name:** `⚡ AI Sales Outreach Automation`
- **Tagline:** `Hyper-personalized B2B outreach — researched, written, and sent by AI agents`
- **Badges (inline):** Python 3.11 · TypeScript · LangGraph · n8n · Claude + GPT-4 · Docker · FastAPI · Next.js 14
  - Use `img.shields.io` static badges with GitHub dark colors
- **Hero description (2 sentences):** Plain-English explanation of what the platform does — CSV in, personalized emails out, replies classified, follow-ups scheduled.

### 2. The Problem

- Section label: `The Problem`
- Headline: `😤 Cold outreach is broken`
- Body: ~2 short paragraphs. Lead with the ~1% reply rate stat. Frame the bottleneck as the research+personalization loop, not the sending volume.

### 3. The Solution

- Section label: `The Solution`
- Headline: `✨ Let AI agents do the research`
- Body: Explain the LangGraph agent pipeline in plain English. End with the product bet: "personalization quality beats volume."

### 4. How It Works — End-to-End Flow

- Section label: `End-to-End Flow`
- Headline: `🔄 How It Works`
- **Mermaid flowchart (LR):** CSV/Sheets → FastAPI → n8n → Research Agent → Personalization Agent → Gmail Send → Reply Classifier → Follow-up Agent
  - Note: Compliance check is part of the Personalization agent (3B) — do not show as a separate node
- Edge label on n8n → Research: `per lead`
- Brief prose paragraph above the diagram explaining the pipeline in one sentence.

### 5. Architecture — Three Planes

- Section label: `System Architecture`
- Headline: `🏗 Three-Plane Architecture`
- **Mermaid flowchart (TB):** Three subgraphs — Interaction Plane (Next.js + FastAPI), Reasoning Plane (LangGraph Agents), Automation Plane (n8n). Arrows: Interaction → Reasoning, Interaction → Automation, Reasoning ↔ Qdrant.
- One-sentence caption per plane in a table below the diagram.

### 6. LangGraph Agents

- Section label: `LangGraph Agents`
- Headline: `🤖 The Agent Pipeline`
- **Markdown table** with columns: Agent | Phase | Responsibility | Key Output
- Rows: Research (3A), Personalization (3B), Reply Classifier (3C), Follow-up (3D)

### 7. Tech Stack

- Section label: `Tech Stack`
- Headline: `🛠 Built With`
- **Markdown table** organized by category: Frontend · Backend · AI/Agents · Automation · Infrastructure
- Each row: Category | Technologies

### 8. Project Phases

- Section label: `Build Status`
- Headline: `📊 Project Phases`
- Simple list with ✅ / ⬜ emoji per phase (0–7), phase name, and one-line note
- Current status: Phases 0–3 complete, 4–7 not started

### 9. Quickstart

- Section label: `Get Started`
- Headline: `⚡ Quickstart`
- Fenced bash code block: `git clone` → `cp .env.example .env` → `make dev` → `make seed`
- Output comments showing the three URLs: frontend (3000), API docs (8000/docs), n8n (5678)
- Note: "See `.env.example` for the full list of required API keys."

---

## Formatting Rules

- Use `---` horizontal rules between major sections (The Problem / The Solution / How It Works / Architecture / Agents / Stack / Phases / Quickstart)
- Section labels rendered as `> **Category**` blockquotes above each `##` heading
- All headings are `##` (H2) — no H3 except inside tables/lists
- No HTML tags — pure Markdown only
- No trailing commentary, task references, or "added for X" comments in the file

---

## Out of Scope

- Animated GIFs or screenshots (frontend not built yet)
- Contributing guide
- License section
- API reference (lives in `docs/04-API.md`)
