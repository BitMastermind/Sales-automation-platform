# /agents — LangGraph Reasoning Layer

This directory contains every LLM-powered agent. The backend never imports OpenAI or Anthropic directly — it imports from here.

> n8n is the pipeline. **LangGraph is the brain.** Never reverse this.

## Why isolate agents
- Swap models/providers without touching FastAPI routes.
- Test reasoning independently of HTTP plumbing.
- Each agent gets its own structured I/O contract via Pydantic.

## Agents
| Agent | File | Purpose |
|-------|------|---------|
| Research | `research_agent.py` | Scrape site + news → industry, pain points, recent activity |
| Personalization | `personalization_agent.py` | Combine research + templates → email draft |
| Compliance | `compliance_agent.py` | Filter spam triggers, false claims, length |
| Email Generator | (merged into personalization) | Final subject + body + CTA |
| Reply Classifier | `reply_classifier.py` | Classify reply intent (interested / not / meeting / unsubscribe) |
| Follow-up | `followup_agent.py` | Day-3 bump, day-7 value-add, day-14 break-up |

Full specs (state schemas, node graph, prompts): [../docs/03-AGENTS.md](../docs/03-AGENTS.md)

## Model Routing (default)
- **Synthesis / extraction:** Claude `claude-sonnet-4-20250514` (smarter at structured extraction)
- **Quality checks / classification:** `gpt-4o-mini` (fast + cheap)
- **Compliance:** Claude — needs nuance on tone

Each agent exposes a single async entry point: `async def run_<name>_agent(...) -> dict`.
