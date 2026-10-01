# agentic-stack

Workflow agêntico com LangGraph + OpenRouter, exposto por uma API própria (FastAPI + SSE), self-hosted em container e consumido por um front Next.js. O usuário entra com email e senha, conversa com o agente (resposta em streaming) e aprova ou recusa as ações que o agente pausa para confirmar, como enviar um email.

## Índice

- [O que tem no projeto](#o-que-tem-no-projeto)
- [Requisitos](#requisitos)
- [Como rodar](#como-rodar)
- [Comandos](#comandos)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Como funciona](#como-funciona)
- [API](#api)
- [Testes e CI](#testes-e-ci)
- [Documentação completa](#documentação-completa)
- [Deploy](#deploy)
- [Próximos passos](#próximos-passos)

## O que tem no projeto

| Área            | Ferramentas                                                                         |
| --------------- | ----------------------------------------------------------------------------------- |
| Agente          | LangGraph (grafo com tools e aprovação humana via `interrupt`), LLM pelo OpenRouter |
| API             | FastAPI + SSE (`sse-starlette`), Python 3.12, uv                                    |
| Persistência    | Postgres: checkpointer do LangGraph, threads, advisory locks (um run por thread)    |
| Autenticação    | Better Auth (email/senha) no web + JWT EdDSA validado pelo agent via JWKS           |
| Front           | Next.js 16, React 19, Tailwind v4 + shadcn/ui, pnpm                                 |
| Contrato        | OpenAPI gerado do Pydantic → tipos TypeScript (openapi-typescript), checado no CI   |
| Testes          | pytest (agent), Vitest + Playwright (web)                                           |
| Deploy          | Imagem do agent no GHCR + VPS com Caddy; web no Vercel                              |
| Observabilidade | Langfuse (opcional)                                                                 |

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala o Python 3.12+ sozinho)
- Node.js 22+ e [pnpm](https://pnpm.io) (o front só aceita pnpm)
- Docker **com o daemon rodando** (Docker Desktop, OrbStack etc.). Sem ele `make db` falha e a API não sobe: ela cria as tabelas no Postgres durante o startup.
- Uma chave do [OpenRouter](https://openrouter.ai/keys)

## Como rodar

1. Arquivos de ambiente:

   ```bash
   cp apps/agent/.env.example apps/agent/.env
   cp apps/web/.env.example apps/web/.env.local
   ```

2. Em `apps/agent/.env`, preencha **`OPENROUTER_API_KEY`**. Sem uma chave válida a API sobe, mas toda mensagem termina com o evento `error` (`internal`). O resto já vem pronto para dev:
   - `DATABASE_URL` aponta para o Postgres do `make db`
   - `AUTH_URL=http://localhost:3000`: endereço do web, de onde vêm as chaves do JWT
   - `AUTH_DISABLED=true` (só vale com `ENV=dev`): requisição **sem** token vira o usuário `dev-user`, útil para testar pelo `/docs` ou curl. Requisições do front sempre levam token, que é validado normalmente.
   - `OPENROUTER_MODEL` pode ser trocado por qualquer modelo do OpenRouter com tool calling

3. Em `apps/web/.env.local`, troque **`BETTER_AUTH_SECRET`** por um segredo seu (`openssl rand -base64 32`). `DATABASE_URL` aponta para o mesmo Postgres do agent e `BETTER_AUTH_URL` precisa ser igual ao `AUTH_URL` do agent.

4. Dependências:

   ```bash
   cd apps/agent && uv sync && cd ../..
   cd apps/web && pnpm install && cd ../..
   ```

5. Suba tudo:

   ```bash
   make dev             # Postgres + tabelas de auth + API (:8000/docs) + web (:3000)
   ```

Abra http://localhost:3000, crie uma conta e converse. Peça "manda um email pra fulano@x.com dizendo oi" para ver o fluxo de aprovação. As tools (`get_weather`, `send_email`) são exemplos e não fazem nada de verdade.

`make dev` junta os logs da API e do web no mesmo terminal. Ctrl+C derruba os dois, mas o Postgres continua rodando (`docker compose stop` para parar). Para logs separados, rode `make db auth-migrate`, depois `make dev-agent` e `make dev-web` em terminais diferentes.

## Comandos

| Comando                           | O que faz                                                             |
| --------------------------------- | --------------------------------------------------------------------- |
| `make dev`                        | Confere os `.env`, sobe Postgres, migra o Better Auth, roda API e web |
| `make db` / `make auth-migrate`   | Só o Postgres / só as tabelas do Better Auth                          |
| `make dev-agent` / `make dev-web` | Só a API (:8000) / só o web (:3000)                                   |
| `make studio`                     | LangGraph Studio, para depurar o grafo                                |
| `make test`                       | pytest + typecheck e testes unitários do web                          |
| `make lint`                       | ruff + ESLint                                                         |
| `make contract`                   | Regenera `openapi.json` e os tipos TypeScript do web                  |
| `make up`                         | Agent + Postgres em containers (o web roda com `make dev-web`)        |

Detalhes de cada alvo em [`docs/config/stack-geral.md`](./docs/config/stack-geral.md#makefile).

## Estrutura do projeto

```
apps/
  agent/                 Python: grafo + API. Deploy: container em VPS
    src/agent/
      graph/             o grafo (state, tools, prompts, builder). Não sabe que HTTP existe
      api/               FastAPI: auth, rotas, tradução stream LangGraph -> SSE
      persistence/       pool Postgres, migrations, threads, advisory locks
      llm.py             ChatOpenAI apontando pro OpenRouter
    openapi.json         CONTRATO (gerado, commitado)
    tests/
  web/                   Next.js 16 + Better Auth + shadcn/ui (pnpm). Deploy: Vercel (root dir = apps/web)
    src/lib/auth.ts      Better Auth (email/senha + plugin jwt), tabelas no Postgres
    src/app/api/auth/    rotas do Better Auth, inclusive /api/auth/jwks
    src/components/      tela de login, chat (componentes message/bubble do shadcn), aprovação
    src/lib/agent/       client tipado + SSE, hook do chat, schema.d.ts (gerado)
    README.md, docs/     detalhes do front (tooling, convenções, testes)
deploy/                  compose de produção + Caddy
docs/                    documentação do projeto como um todo
```

## Como funciona

```
browser ──login (cookie)──▶ web /api/auth/*  ──▶ Postgres, schema auth (user, session, jwks…)
   │                            │
   │  GET /api/auth/token       │ JWKS público em /api/auth/jwks
   ▼                            ▼
 JWT EdDSA (15 min) ──Bearer──▶ agent: valida assinatura (JWKS), iss/aud = AUTH_URL, exp
                                 `sub` = id do usuário = dono das threads
```

- **Um Postgres, dois schemas**: `auth` (Better Auth, só o web acessa) e `agent` (threads e checkpoints, só o agent acessa).
- **O agent nunca lê sessão nem cookie**: só valida o JWT emitido pelo web. `X-API-Key` (+ `X-User-Id`) serve para chamadas servidor-a-servidor.
- **Aprovação humana**: a tool chama `interrupt()`, o grafo pausa e salva o estado; o front mostra o pedido e a resposta retoma o grafo de onde parou.

Mais em [`docs/config/autenticacao.md`](./docs/config/autenticacao.md) e [`docs/config/agent.md`](./docs/config/agent.md).

## API

Tudo sob `/v1`. Auth: `Authorization: Bearer <jwt do Better Auth>` ou `X-API-Key` (+ `X-User-Id`).

| Método | Rota                        | O quê                                           |
| ------ | --------------------------- | ----------------------------------------------- |
| POST   | `/threads`                  | Cria thread                                     |
| GET    | `/threads`                  | Lista threads do usuário                        |
| GET    | `/threads/{id}`             | Estado: mensagens, `next`, interrupts pendentes |
| DELETE | `/threads/{id}`             | Apaga thread + checkpoints                      |
| POST   | `/threads/{id}/runs/stream` | Nova mensagem, resposta SSE                     |
| POST   | `/threads/{id}/runs/resume` | Responde interrupt, resposta SSE                |
| POST   | `/threads/{id}/runs/wait`   | Nova mensagem, resposta JSON (sem SSE)          |

Eventos SSE: `run_started`, `token`, `message`, `interrupt`, `done`, `error` (`thread_busy` | `timeout` | `internal`). Um run por thread; mandar mensagem com interrupt pendente dá 409 `pending_interrupt`.

Mudou um schema da API? Rode `make contract` e commite `openapi.json` e `schema.d.ts` juntos. Ver [`docs/config/contrato-api.md`](./docs/config/contrato-api.md).

## Testes e CI

```bash
make test                      # pytest + typecheck e testes unitários do web
make lint                      # ruff + eslint
cd apps/web && pnpm test:e2e   # opcional: Playwright contra um build de produção
```

O CI (`.github/workflows/agent.yml`) roda lint, testes e `make check-contract` nos dois apps e publica a imagem do agent no GHCR a cada push na `main`. Ele, o `check-contract` e os hooks do Husky pressupõem que este diretório é a raiz do repositório git. Ver [`docs/config/testes.md`](./docs/config/testes.md).

## Documentação completa

Para entender **como e por quê** cada parte está configurada:

- [`docs/config/stack-geral.md`](./docs/config/stack-geral.md): monorepo, ferramentas, `Makefile`, arquivos de ambiente e portas.
- [`docs/config/agent.md`](./docs/config/agent.md): grafo, tools e interrupts, OpenRouter, rotas, SSE, observabilidade.
- [`docs/config/autenticacao.md`](./docs/config/autenticacao.md): Better Auth, JWT entre web e agent, API keys, armadilhas.
- [`docs/config/banco-de-dados.md`](./docs/config/banco-de-dados.md): schemas, migrações, pool, advisory locks, poolers.
- [`docs/config/contrato-api.md`](./docs/config/contrato-api.md): OpenAPI → TypeScript e o client do web.
- [`docs/config/testes.md`](./docs/config/testes.md): suítes de teste e pipeline de CI.
- [`docs/config/deploy.md`](./docs/config/deploy.md): VPS com Caddy, Vercel, Postgres e ordem do primeiro deploy.
- [`docs/notas.md`](./docs/notas.md): registro cronológico de decisões e aprendizados.

O front tem documentação própria de tooling (ESLint, Prettier, Tailwind/shadcn, Husky) em [`apps/web/docs/`](./apps/web/docs) e no [`apps/web/README.md`](./apps/web/README.md).

## Deploy

- **Postgres**: qualquer Postgres 14+ acessível pelo agent e pelo web, por conexão direta ou pooler em modo session.
- **agent**: o CI publica a imagem no GHCR; na VPS, `deploy/` + `agent.env` e `docker compose up -d`, atrás do Caddy.
- **web**: Vercel com root directory `apps/web`. Rode `pnpm auth:migrate` contra o banco de produção antes do primeiro deploy.

Passo a passo e variáveis em [`docs/config/deploy.md`](./docs/config/deploy.md).

## Próximos passos

- Rate limit por usuário (antes de abrir publicamente: o custo do LLM é o risco real)
- Integração real nas tools (`send_email` ainda não envia nada)
- Worker (arq/Redis) se os runs passarem de poucos minutos ou precisarem sobreviver a uma desconexão
- Vários grafos: registry `{"nome": build_fn}` e rota `/v1/graphs/{nome}/...`
- Lista de conversas no front (a API já tem `GET /v1/threads`)
