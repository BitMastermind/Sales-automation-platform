# /infra — Docker Compose & Ops

Local-first deployment. Everything runs through `docker compose up`.

## Services
| Service | Image | Port | Notes |
|---------|-------|------|-------|
| postgres | `postgres:15` | 5432 | Volume `pgdata` |
| qdrant | `qdrant/qdrant:latest` | 6333 | Volume `qdrantdata` |
| redis | `redis:7-alpine` | 6379 | Rate limits, queues |
| n8n | `n8nio/n8n:latest` | 5678 | Volume `n8ndata`; webhook URL from `.env` |
| backend | local Dockerfile | 8000 | Hot reload via volume mount |
| frontend | local Dockerfile | 3000 | Hot reload via volume mount |

Full compose spec, healthchecks, Makefile, and Dockerfile structure: [../docs/07-DEPLOYMENT.md](../docs/07-DEPLOYMENT.md)

## Quickstart
```bash
cp .env.example .env      # fill in real keys
make dev                  # docker compose up --build
make migrate              # run alembic migrations
make seed                 # insert demo campaign + 3 leads
```
Verify with: `docker compose ps` — all services should be `healthy`.
