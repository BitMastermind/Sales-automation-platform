# /docs — Project Documentation

The single source of truth for architecture, schemas, agents, and operations.
`CLAUDE.md` at the repo root links to every file here.

## Index
| Doc | What's inside |
|-----|---------------|
| [00-ARCHITECTURE.md](00-ARCHITECTURE.md) | End-to-end data flow, component responsibilities, why this split |
| [01-PHASES.md](01-PHASES.md) | The 8-phase build plan (0 → 7) — phase goals and verification commands |
| [02-DATABASE.md](02-DATABASE.md) | Postgres tables, indexes, Qdrant collections |
| [03-AGENTS.md](03-AGENTS.md) | LangGraph agent specs: state, nodes, prompts, outputs |
| [04-API.md](04-API.md) | FastAPI route reference (request/response shapes) |
| [05-N8N-WORKFLOWS.md](05-N8N-WORKFLOWS.md) | n8n workflow node-by-node specs |
| [06-FRONTEND.md](06-FRONTEND.md) | Page-by-page UX spec for the Next.js dashboard |
| [07-DEPLOYMENT.md](07-DEPLOYMENT.md) | Docker Compose, Dockerfiles, Makefile, env vars |
| [CLAUDE-CODE-GUIDE.md](CLAUDE-CODE-GUIDE.md) | How to prompt Claude Code productively on this repo |
| **[prompts/README.md](prompts/README.md)** | **← Start here when coding. Copy-paste prompts, models, and skills per phase.** |

## Authoring rules
- One concept per file. Cross-link liberally with relative paths.
- Code samples must be runnable (or marked `pseudocode`).
- Architecture diagrams as ASCII first, image only if it actually clarifies.
- When a doc goes stale, update it in the same PR as the code change.
