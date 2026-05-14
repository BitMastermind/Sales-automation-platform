# Project Scratchpad

## Phase 0 — Scaffold (2026-05-14)

- Python on this machine is 3.14 (not 3.11 as spec'd); pyproject.toml uses `>=3.11` so it's satisfied. venv lives at `backend/.venv` — use `.venv/bin/pytest` to run tests.
- Node is v25.2.1; `npx tsc --noEmit` fails due to a shebang issue with the tsc wrapper — use `node node_modules/typescript/lib/tsc.js --noEmit` instead.
- `npx create-next-app` cannot overwrite a non-empty directory, so the Next.js scaffold was generated in `/tmp/next-scaffold/frontend` and copied over.
- Added `required: false` to `env_file` entries in `docker-compose.yml` so `docker compose config` passes without a `.env` file present (copy `.env.example` to `.env` before running `make dev`).
- Alembic `[tool.hatch.build.targets.wheel]` packages section is required for editable install with non-src layout.
- shadcn/ui v4 (Tailwind v4) detected; `components.json` generated with Default style, Slate base, CSS variables enabled.
