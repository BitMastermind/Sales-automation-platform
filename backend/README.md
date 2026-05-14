# /backend — FastAPI Application

The API layer that the frontend, n8n, and external webhooks talk to. It is *not* allowed to call LLMs directly — every reasoning call goes through `/agents`.

## Stack
- FastAPI + Uvicorn
- Python 3.11
- SQLAlchemy 2.0 (async) + Alembic
- Pydantic v2
- `google-auth-oauthlib` (Gmail OAuth — raw Google API client, no third-party wrappers)
- `qdrant-client` (async)
- Redis for rate limiting

## Folder Layout
```
/backend
├── api/                # FastAPI routers (campaigns, leads, emails, webhooks, auth)
├── core/               # Config, DB session, vector store, logging
├── models/             # SQLAlchemy ORM models
├── services/           # Business logic (gmail_service, lead_importer, ...)
├── agents_interface/   # Thin client that calls /agents (the ONLY way backend hits LLMs)
├── tests/              # pytest, pytest-asyncio, respx, factory-boy
└── pyproject.toml
```

## API Surface
Detailed reference: [../docs/04-API.md](../docs/04-API.md)

## Conventions
- All endpoints return `{ "data": ..., "error": null, "meta": {...} }`.
- All async — never block the event loop.
- All IDs are UUIDs, all timestamps UTC.
- Logging via `logging` module, never `print`.

## Run Locally
```bash
make dev        # boots full stack via Docker Compose
make migrate    # alembic upgrade head
make test       # pytest backend/tests/ -v
```
