# Project Scratchpad

## Phase 1 — Data Layer (2026-05-14)

- Local Postgres (PID bound to localhost:5432) intercepts connections before Docker's mapped port. Created `sales` role + `sales` + `sales_test` databases in the local instance. Pass `DATABASE_URL` env var explicitly when running `alembic` CLI.
- `greenlet` is NOT in `pyproject.toml` but is a required runtime dep of SQLAlchemy 2.0 async on Python 3.14. Added manually with `pip install greenlet`. Should be added to `pyproject.toml` dependencies.
- SQLAlchemy `Enum` column `server_default`: pass the bare value string e.g. `server_default="draft"` — **not** `server_default="'draft'"`. SQLAlchemy adds its own quoting for PostgreSQL enum types. Double-quoting causes `invalid input value for enum` errors.
- Alembic autogenerate correctly strips redundant quotes when it sees `"'draft'"` in models and outputs `'draft'` (plain string) in the migration file. The models and migration file now agree on `"draft"` form.
- `conftest.py` uses a sync `scope="session"` fixture with `asyncio.run()` to create tables before tests start. This avoids event-loop scope conflicts with `pytest-asyncio` 1.x.

## Phase 0 — Scaffold (2026-05-14)

- Python on this machine is 3.14 (not 3.11 as spec'd); pyproject.toml uses `>=3.11` so it's satisfied. venv lives at `backend/.venv` — use `.venv/bin/pytest` to run tests.
- Node is v25.2.1; `npx tsc --noEmit` fails due to a shebang issue with the tsc wrapper — use `node node_modules/typescript/lib/tsc.js --noEmit` instead.
- `npx create-next-app` cannot overwrite a non-empty directory, so the Next.js scaffold was generated in `/tmp/next-scaffold/frontend` and copied over.
- Added `required: false` to `env_file` entries in `docker-compose.yml` so `docker compose config` passes without a `.env` file present (copy `.env.example` to `.env` before running `make dev`).
- Alembic `[tool.hatch.build.targets.wheel]` packages section is required for editable install with non-src layout.
- shadcn/ui v4 (Tailwind v4) detected; `components.json` generated with Default style, Slate base, CSS variables enabled.
