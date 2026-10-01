# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**agentic-stack**: an agentic workflow (LangGraph + OpenRouter) exposed through its own API (FastAPI + SSE), self-hosted in a container, and consumed by a Next.js front-end. Users sign in, chat with the agent (streamed responses), and approve or refuse actions the agent pauses on before they run (LangGraph interrupts, e.g. sending an email). The tools shipped today (`get_weather`, `send_email`) are examples with no real side effects.

Monorepo with two apps sharing one Postgres:

- `apps/agent` — Python 3.12 (uv): the LangGraph graph plus the FastAPI API. Deployed as a container on a VPS behind Caddy.
- `apps/web` — Next.js 16 (pnpm): Better Auth (email/password) + chat UI. Deployed on Vercel. Has its own `CLAUDE.md`, `README.md` and `docs/` — read them before touching the front-end; this file covers the project as a whole.

## Commands

Run from the repo root (see `Makefile`):

- `make dev` — checks env files, starts Postgres, runs Better Auth migrations, then API (:8000) + web (:3000) in one terminal
- `make db` / `make auth-migrate` / `make dev-agent` / `make dev-web` — the same pieces individually
- `make studio` — LangGraph Studio for the graph
- `make test` — agent pytest + web typecheck and unit tests
- `make lint` — ruff (agent) + eslint (web)
- `make contract` — regenerate `apps/agent/openapi.json` and `apps/web/src/lib/agent/schema.d.ts`; `make check-contract` fails if they are stale (CI, needs git)
- `make up` — agent + Postgres in containers (web still runs via `make dev-web`)
- Single agent test: `cd apps/agent && uv run pytest tests/test_auth.py -k hs256`
- Web-only commands (`pnpm test:e2e`, single tests, formatting): see `apps/web/CLAUDE.md`

Package managers are fixed per app: `uv` in `apps/agent`, `pnpm` in `apps/web` (never npm/yarn there).

## Architecture

- **Graph knows nothing about HTTP**: `apps/agent/src/agent/graph/` (state, tools, prompts, builder) is pure LangGraph; `api/` translates it to HTTP/SSE; `persistence/` owns Postgres. Keep it that way — tests build the graph with a fake LLM and an in-memory checkpointer.
- **Human approval = `interrupt()` inside the tool** (`graph/tools.py`). On resume the tool re-runs from the start, so nothing with side effects may come before the `interrupt` call.
- **One Postgres, two schemas**: `auth` (Better Auth tables, only the web touches them) and `agent` (threads + LangGraph checkpoints, only the agent touches them). Both apps pin `search_path`; the default `"$user", public` silently put tables in the wrong schema once.
- **Auth across apps is a JWT, not a shared session**: the web's Better Auth `jwt` plugin issues 15‑min EdDSA tokens and serves `/api/auth/jwks`; the agent (`api/auth.py`) validates signature, `iss`/`aud` (= `AUTH_URL`, must equal the web's `BETTER_AUTH_URL`) and `exp`. `sub` is the thread owner. `X-API-Key` + `X-User-Id` is the server-to-server path.
- **One run per thread** via a Postgres session advisory lock (`persistence/locks.py`) — works across replicas, and is why a transaction-mode pooler is not supported.
- **The API contract is generated and committed**: Pydantic schemas in `api/schemas.py` → `openapi.json` (including the `StreamEvent` union injected in `api/main.py`) → `schema.d.ts` via openapi-typescript. Never edit the generated files by hand.

Deep dives for each area live in `docs/config/` — read the relevant one before non-trivial changes:
`stack-geral.md` (monorepo, tooling, Makefile, env files), `agent.md` (graph, LLM, API, SSE), `autenticacao.md` (Better Auth ↔ agent JWT), `banco-de-dados.md` (schemas, migrations, locks, pooling), `contrato-api.md` (OpenAPI → TS), `testes.md` (test suites and CI), `deploy.md` (VPS/Caddy, Vercel, GHCR).

## Keeping docs current

- `docs/config/*.md` is the source of truth for _how and why_ each cross-cutting part is configured. When you change it non-cosmetically (auth flow, schemas/migrations, API contract, CI, deploy, Makefile, env vars), update the matching doc — or add one — instead of letting it drift. Front-end tooling changes go in `apps/web/docs/` instead.
- `docs/notas.md` is the chronological log of project-wide decisions, constraints and non-obvious learnings. Add a dated entry when a future session would otherwise have to rediscover something.
- Update the root `README.md` (onboarding + run instructions) and this file when commands, architecture or conventions change.
