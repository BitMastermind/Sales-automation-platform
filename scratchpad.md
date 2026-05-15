# Project Scratchpad

## Phase 1 — Data Layer (2026-05-14)

- Local Postgres (PID bound to localhost:5432) intercepts connections before Docker's mapped port. Created `sales` role + `sales` + `sales_test` databases in the local instance. Pass `DATABASE_URL` env var explicitly when running `alembic` CLI.
- `greenlet` is NOT in `pyproject.toml` but is a required runtime dep of SQLAlchemy 2.0 async on Python 3.14. Added manually with `pip install greenlet`. Should be added to `pyproject.toml` dependencies.
- SQLAlchemy `Enum` column `server_default`: pass the bare value string e.g. `server_default="draft"` — **not** `server_default="'draft'"`. SQLAlchemy adds its own quoting for PostgreSQL enum types. Double-quoting causes `invalid input value for enum` errors.
- Alembic autogenerate correctly strips redundant quotes when it sees `"'draft'"` in models and outputs `'draft'` (plain string) in the migration file. The models and migration file now agree on `"draft"` form.
- `conftest.py` uses a sync `scope="session"` fixture with `asyncio.run()` to create tables before tests start. This avoids event-loop scope conflicts with `pytest-asyncio` 1.x.

## Phase 2B — Gmail OAuth + GmailService (2026-05-15)

- `google-api-python-client` uses `httplib2` for API calls (not httpx) — not mockable with `respx`. Mocked at the `build()` level using `unittest.mock.patch("services.gmail_service.build")` instead.
- Token exchange AND refresh both use `httpx.AsyncClient` (manual grant calls), not `google-auth-oauthlib` Flow — this keeps them mockable with `respx` and avoids the synchronous `run_local_server()` path.
- Token refresh race condition: `asyncio.Lock` per `GmailService` instance is sufficient for single-worker MVP. Multi-worker would need Redis or `SELECT FOR UPDATE`.
- `db_session` fixture in conftest doesn't truncate between tests (unlike `async_client`). Tests that write DB rows in one test and need isolation in the next must add their own `DELETE` autouse fixture — see `test_gmail_service.py::clear_oauth_tokens`.
- `scalar_one_or_none()` throws `MultipleResultsFound` if two gmail tokens exist. Changed to `.scalars().first()` for resilience (single-user MVP can only have one, but defensive coding matters).
- Fernet key generation command added to `.env.example`: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- Exception handlers registered in `main.py` via `register_exception_handlers(app)` — returns standard `{"data": null, "error": {...}, "meta": {}}` envelope shape.

## Phase 0 — Scaffold (2026-05-14)

- Python on this machine is 3.14 (not 3.11 as spec'd); pyproject.toml uses `>=3.11` so it's satisfied. venv lives at `backend/.venv` — use `.venv/bin/pytest` to run tests.
- Node is v25.2.1; `npx tsc --noEmit` fails due to a shebang issue with the tsc wrapper — use `node node_modules/typescript/lib/tsc.js --noEmit` instead.
- `npx create-next-app` cannot overwrite a non-empty directory, so the Next.js scaffold was generated in `/tmp/next-scaffold/frontend` and copied over.
- Added `required: false` to `env_file` entries in `docker-compose.yml` so `docker compose config` passes without a `.env` file present (copy `.env.example` to `.env` before running `make dev`).
- Alembic `[tool.hatch.build.targets.wheel]` packages section is required for editable install with non-src layout.
- shadcn/ui v4 (Tailwind v4) detected; `components.json` generated with Default style, Slate base, CSS variables enabled.
