.PHONY: dev migrate test lint seed

dev: ## Boot the full stack with logs
	docker compose -f infra/docker-compose.yml up --build

migrate: ## Run Alembic migrations inside backend container
	docker compose -f infra/docker-compose.yml exec backend alembic upgrade head

test: ## Run pytest inside backend container
	docker compose -f infra/docker-compose.yml exec backend pytest -v

lint: ## Ruff + mypy (backend), eslint (frontend)
	docker compose -f infra/docker-compose.yml exec backend ruff check .
	docker compose -f infra/docker-compose.yml exec backend mypy .
	docker compose -f infra/docker-compose.yml exec frontend npm run lint

seed: ## Create one demo campaign with 3 leads
	docker compose -f infra/docker-compose.yml exec backend python scripts/seed.py
