.PHONY: env-check db auth-migrate dev dev-agent dev-web studio test lint contract check-contract up

db:            ## Postgres local
	docker compose up -d --wait postgres

env-check:     ## Falha cedo, com o comando certo, se faltar arquivo de env
	@test -f apps/agent/.env || { echo "Falta apps/agent/.env. Rode: cp apps/agent/.env.example apps/agent/.env (e preencha OPENROUTER_API_KEY)"; exit 1; }
	@test -f apps/web/.env.local || { echo "Falta apps/web/.env.local. Rode: cp apps/web/.env.example apps/web/.env.local (e troque BETTER_AUTH_SECRET)"; exit 1; }

auth-migrate:  ## Cria/atualiza as tabelas do Better Auth (idempotente)
	cd apps/web && pnpm -s auth:migrate

dev: env-check db auth-migrate  ## Postgres + API + web no mesmo terminal. Ctrl+C para tudo (o Postgres continua)
	$(MAKE) -j2 dev-agent dev-web

dev-agent:     ## API com reload
	cd apps/agent && uv run uvicorn agent.api.main:app --reload --port 8000

studio:        ## LangGraph Studio (debug visual do grafo)
	cd apps/agent && uv run langgraph dev

dev-web:
	cd apps/web && pnpm dev

test:
	cd apps/agent && uv run pytest
	cd apps/web && pnpm typecheck && pnpm test

lint:
	cd apps/agent && uv run ruff check . && uv run ruff format --check .
	cd apps/web && pnpm lint

contract:      ## Regenera openapi.json e os tipos TS. Rode após mudar schemas da API.
	cd apps/agent && uv run python scripts/export_openapi.py > openapi.json
	cd apps/web && pnpm -s gen:agent-types

check-contract: contract  ## Usado no CI: falha se o contrato commitado está desatualizado
	git diff --exit-code apps/agent/openapi.json apps/web/src/lib/agent/schema.d.ts

up:            ## Stack completa em containers
	docker compose up --build
