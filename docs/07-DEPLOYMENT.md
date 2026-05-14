# 07 — Deployment

Local-first. `docker compose up` boots the entire system.

## File map
```
/infra
├── docker-compose.yml
├── nginx/                  # (optional, prod reverse proxy)
└── README.md
/backend/Dockerfile         # multi-stage, non-root
/frontend/Dockerfile        # multi-stage, non-root
/.env.example               # required keys
/Makefile                   # dev shortcuts
```

## `docker-compose.yml` services

| Service | Image | Port | Volume | Healthcheck |
|---------|-------|------|--------|-------------|
| postgres | `postgres:15` | 5432 | `pgdata:/var/lib/postgresql/data` | `pg_isready` |
| qdrant | `qdrant/qdrant:latest` | 6333 | `qdrantdata:/qdrant/storage` | HTTP `/healthz` |
| redis | `redis:7-alpine` | 6379 | `redisdata:/data` | `redis-cli ping` |
| n8n | `n8nio/n8n:latest` | 5678 | `n8ndata:/home/node/.n8n` | HTTP `/healthz` |
| backend | build `./backend` | 8000 | `./backend:/app` (dev hot reload) | HTTP `/health` |
| frontend | build `./frontend` | 3000 | `./frontend:/app` (dev hot reload) | HTTP `/` |

All services share a single bridge network (`saleshq`). The backend `depends_on: { postgres, qdrant, redis }` with `condition: service_healthy`.

## Dockerfiles

### `/backend/Dockerfile` (multi-stage)
1. **builder** — `python:3.11-slim`, install build deps, `pip install --prefix=/install .`.
2. **runtime** — `python:3.11-slim`, copy from `/install`, run as non-root user `app`. Entry: `uvicorn main:app --host 0.0.0.0 --port 8000`.

### `/frontend/Dockerfile` (multi-stage)
1. **deps** — `node:20-alpine`, `npm ci`.
2. **builder** — `npm run build`.
3. **runner** — `node:20-alpine`, non-root, copies `.next/standalone`, runs `node server.js`.

Each Dockerfile is paired with a `.dockerignore` (at minimum: `node_modules`, `__pycache__`, `.venv`, `.next`, `.env*`).

## `.env.example`
```dotenv
# Postgres
DATABASE_URL=postgresql+asyncpg://sales:sales@postgres:5432/sales

# Qdrant
QDRANT_URL=http://qdrant:6333

# Redis
REDIS_URL=redis://redis:6379/0

# LLMs
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Research tooling
TAVILY_API_KEY=
FIRECRAWL_API_KEY=

# Gmail OAuth
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=

# n8n
N8N_WEBHOOK_URL=http://n8n:5678/webhook
INTERNAL_API_TOKEN=change-me-long-random

# Frontend
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Makefile

```makefile
dev:        ## Boot the full stack with logs
	docker compose -f infra/docker-compose.yml up --build

migrate:    ## Run Alembic migrations inside backend container
	docker compose exec backend alembic upgrade head

test:       ## Run pytest inside backend container
	docker compose exec backend pytest -v

seed:       ## Create one demo campaign with 3 leads
	docker compose exec backend python scripts/seed.py

lint:       ## Ruff + mypy (backend), eslint (frontend)
	docker compose exec backend ruff check .
	docker compose exec backend mypy .
	docker compose exec frontend npm run lint
```

## Verification
1. `cp .env.example .env`, fill in real keys.
2. `make dev` — watch logs; all services should announce `healthy`.
3. `make migrate` — Alembic upgrades to head.
4. `make seed` — demo data exists.
5. Visit `http://localhost:3000` — dashboard renders, campaigns list non-empty.
6. Visit `http://localhost:5678` — n8n UI loads.
7. Hit `http://localhost:8000/docs` — FastAPI Swagger UI loads.

If any healthcheck fails, fix it before opening a PR.
