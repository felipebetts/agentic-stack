# Stack geral

Visão geral de como o monorepo está organizado: apps, ferramentas de cada um, o `Makefile` que amarra tudo e os arquivos de ambiente. Para cada área específica (agent, autenticação, banco, contrato, testes, deploy), veja os documentos irmãos nesta pasta. O tooling interno do front (ESLint, Prettier, Tailwind, Husky) está documentado em [`apps/web/docs/config/`](../../apps/web/docs/config).

## Layout do monorepo

```
├── apps/
│   ├── agent/             # Python: grafo LangGraph + API FastAPI (uv)
│   └── web/               # Next.js 16: Better Auth + UI do chat (pnpm)
├── deploy/                # compose de produção (agent + Caddy) e Caddyfile
├── docs/                  # esta documentação (visão do projeto inteiro)
├── .github/workflows/     # CI: testes, contrato e imagem do agent
├── docker-compose.yml     # dev: Postgres (e o agent, via `make up`)
└── Makefile               # ponto de entrada de todos os comandos do dia a dia
```

Os dois apps são independentes em build e deploy (o agent vira uma imagem Docker; o web vai para o Vercel), mas compartilham:

- **um Postgres**, cada app no seu schema (ver [`banco-de-dados.md`](./banco-de-dados.md));
- **o contrato da API** (`apps/agent/openapi.json` → `apps/web/src/lib/agent/schema.d.ts`, ver [`contrato-api.md`](./contrato-api.md));
- **a confiança de autenticação**: o web emite JWTs que o agent valida (ver [`autenticacao.md`](./autenticacao.md)).

Não existe workspace JS nem Python na raiz: cada app instala as próprias dependências dentro da sua pasta.

## Ferramentas por app

| App          | Linguagem  | Gerenciador                      | Versão        | Onde está fixada                                                     |
| ------------ | ---------- | -------------------------------- | ------------- | -------------------------------------------------------------------- |
| `apps/agent` | Python     | [uv](https://docs.astral.sh/uv/) | Python ≥ 3.12 | `pyproject.toml` (`requires-python`), `langgraph.json`, `Dockerfile` |
| `apps/web`   | TypeScript | pnpm (único aceito)              | Node 22 LTS   | `.nvmrc` (`lts/jod`), `package.json#packageManager`                  |

- **uv** cria o `.venv` e instala o Python certo sozinho (`uv sync`). O `uv.lock` é commitado; o CI usa `uv sync --frozen`.
- **pnpm** é obrigatório no web (o template de origem só suporta pnpm). O `pnpm-lock.yaml` é commitado; o CI usa `pnpm install --frozen-lockfile`.
- **Docker** (Docker Desktop, OrbStack etc.) é necessário em dev para o Postgres. O daemon precisa estar rodando antes do `make dev`.

## `Makefile`

Todos os comandos do dia a dia partem da raiz:

| Alvo                  | O que faz                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------ |
| `make dev`            | `env-check` → `db` → `auth-migrate` → API e web em paralelo (`make -j2`), logs no mesmo terminal |
| `make env-check`      | Falha cedo, com o `cp` certo, se faltar `apps/agent/.env` ou `apps/web/.env.local`               |
| `make db`             | Sobe o Postgres do `docker-compose.yml` e espera ficar saudável (`--wait`)                       |
| `make auth-migrate`   | Cria o schema `auth` e as tabelas do Better Auth (idempotente)                                   |
| `make dev-agent`      | API com reload em `:8000` (`uvicorn --reload`)                                                   |
| `make dev-web`        | Next em `:3000` (`pnpm dev`)                                                                     |
| `make studio`         | LangGraph Studio (`langgraph dev`) para depurar o grafo visualmente                              |
| `make test`           | `pytest` do agent + `typecheck` e testes unitários do web                                        |
| `make lint`           | `ruff check` + `ruff format --check` no agent, ESLint no web                                     |
| `make contract`       | Regenera `openapi.json` e `schema.d.ts`                                                          |
| `make check-contract` | `contract` + `git diff --exit-code` nos dois arquivos (usado no CI)                              |
| `make up`             | Agent + Postgres em containers (`docker compose up --build`)                                     |

- **`make dev` não para o Postgres** no Ctrl+C: ele roda em background pelo compose. Use `docker compose stop` para parar.
- **`make -j2`** junta os logs dos dois processos. Para logs separados, rode `make db auth-migrate` e depois `make dev-agent` e `make dev-web` em terminais diferentes.
- **`make up`** não inclui o web: o agent em container busca o JWKS do web rodando no host via `host.docker.internal` (variável `AUTH_JWKS_URL` no `docker-compose.yml`).

## Arquivos de ambiente

Cada app tem seu template versionado; os arquivos reais são ignorados pelo git.

| Arquivo               | Template                  | Lido por                                                                          |
| --------------------- | ------------------------- | --------------------------------------------------------------------------------- |
| `apps/agent/.env`     | `apps/agent/.env.example` | `pydantic-settings` (`src/agent/config.py`), `langgraph dev`, `docker compose`    |
| `apps/web/.env.local` | `apps/web/.env.example`   | Next.js, `pnpm auth:migrate` (`node --env-file-if-exists`) e a CLI do Better Auth |

Variáveis que **precisam combinar** entre os dois apps:

| Agent          | Web                     | Regra                                                                       |
| -------------- | ----------------------- | --------------------------------------------------------------------------- |
| `AUTH_URL`     | `BETTER_AUTH_URL`       | Iguais. Viram o `iss`/`aud` do JWT; se diferirem, o agent recusa todo token |
| `DATABASE_URL` | `DATABASE_URL`          | Mesmo banco (schemas diferentes)                                            |
| `CORS_ORIGINS` | URL pública do web      | O agent precisa liberar a origem do web                                     |
| —              | `NEXT_PUBLIC_AGENT_URL` | Endereço da API do agent visto pelo navegador                               |

Variáveis principais do agent (lista completa e defaults em `src/agent/config.py`):

| Variável                                  | Default                            | Para quê                                                                             |
| ----------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------ |
| `OPENROUTER_API_KEY`                      | — (obrigatória)                    | Chave do OpenRouter. Inválida: a API sobe, mas todo run termina em `error: internal` |
| `OPENROUTER_MODEL`                        | `anthropic/claude-sonnet-4.5`      | Modelo (precisa suportar tool calling)                                               |
| `OPENROUTER_PROVIDER_ORDER`               | `[]`                               | Restringe providers do OpenRouter (JSON)                                             |
| `DATABASE_URL` / `DB_SCHEMA`              | — / `agent`                        | Postgres e schema do agent                                                           |
| `AUTH_URL` / `AUTH_JWKS_URL`              | `http://localhost:3000` / derivada | Validação do JWT (ver [`autenticacao.md`](./autenticacao.md))                        |
| `SERVICE_API_KEYS`                        | `[]`                               | Chaves para chamadas servidor-a-servidor (JSON)                                      |
| `AUTH_DISABLED`                           | `false`                            | Só com `ENV=dev`: requisição sem credencial vira `dev-user`                          |
| `CORS_ORIGINS`                            | `["http://localhost:3000"]`        | Origens liberadas (JSON)                                                             |
| `RUN_TIMEOUT_SECONDS` / `RECURSION_LIMIT` | `300` / `25`                       | Limites por run                                                                      |
| `LANGFUSE_*`                              | —                                  | Tracing opcional (requer o extra `langfuse`)                                         |

As variáveis do web estão documentadas em [`apps/web/README.md`](../../apps/web/README.md#variáveis-de-ambiente).

## Portas em dev

| Serviço                 | Porta                                           |
| ----------------------- | ----------------------------------------------- |
| Web (Next)              | 3000                                            |
| API do agent            | 8000 (`/docs` = Swagger, `/healthz`, `/readyz`) |
| Postgres                | 5432 (usuário/senha/banco `agent`)              |
| E2E do web (Playwright) | 3100                                            |
