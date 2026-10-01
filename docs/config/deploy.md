# Deploy

Três peças em produção: o **agent** em container numa VPS atrás do Caddy, o **web** no Vercel e um **Postgres** gerenciado (ou próprio) acessível pelos dois.

```
navegador ──▶ Vercel (apps/web) ──▶ Postgres (schema auth)
    │
    └── Bearer JWT ──▶ Caddy (TLS) ──▶ agent (container) ──▶ Postgres (schema agent)
                                            └──▶ OpenRouter
```

## Ordem do primeiro deploy

1. **Postgres** de pé, com uma `DATABASE_URL` que os dois apps alcancem.
2. **Tabelas do Better Auth**: `cd apps/web && DATABASE_URL=… pnpm auth:migrate` contra o banco de produção. As tabelas do agent são criadas sozinhas no startup dele.
3. **Web no Vercel**, para ter a URL pública (o agent precisa dela).
4. **Agent na VPS**, com `AUTH_URL` e `CORS_ORIGINS` apontando para essa URL.
5. No Vercel, `NEXT_PUBLIC_AGENT_URL` = domínio do agent. Mudou essa variável? Faça um novo build: ela é embutida no bundle.

## Postgres

- Qualquer Postgres 14+.
- Conexão **direta ou por pooler em modo session**. Modo transaction quebra os advisory locks do agent (ver [`banco-de-dados.md`](./banco-de-dados.md#um-run-por-thread-advisory-lock)).
- O web no Vercel abre conexões a partir de funções serverless; se o provedor limitar conexões, prefira o endpoint com pooler (em modo session) para o web também.

## Agent (VPS)

### Imagem

`apps/agent/Dockerfile`, em dois estágios:

- **Build**: `python:3.12-slim` + `uv` (binário copiado de `ghcr.io/astral-sh/uv`), `uv sync --frozen --no-dev`. Dependências e código vêm em camadas separadas, para reaproveitar o cache. Extras opcionais via `--build-arg UV_EXTRAS="--extra langfuse"`.
- **Runtime**: só o `.venv`, usuário sem privilégios (`app`, uid 1000), `HEALTHCHECK` em `/healthz`.
- **Comando**: `uvicorn` com **1 worker por container** (escale com mais containers, já que o lock por thread fica no Postgres), `--proxy-headers` para confiar no Caddy e 30 s de _graceful shutdown_.

### Publicação (CI)

O job `image` de `.github/workflows/agent.yml` roda em todo push na `main` depois dos testes. Ele publica `ghcr.io/<owner>/<repo>/agent:<sha>` e `:latest` com cache do GitHub Actions. O deploy na VPS ainda é manual: não há job de SSH.

### Na VPS

```
deploy/
├── docker-compose.prod.yml   # agent (imagem do GHCR) + caddy
├── Caddyfile                 # TLS automático + proxy para o agent
└── agent.env                 # você cria; mesmas variáveis do apps/agent/.env.example
```

```bash
cd deploy
export GH_REPO=<owner>/<repo> AGENT_DOMAIN=api.exemplo.com   # AGENT_TAG opcional (padrão: latest)
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

O `agent.env` de produção precisa de:

| Variável             | Valor                                                                      |
| -------------------- | -------------------------------------------------------------------------- |
| `ENV`                | qualquer coisa diferente de `dev` (ex.: `prod`): desliga o `AUTH_DISABLED` |
| `OPENROUTER_API_KEY` | chave real                                                                 |
| `DATABASE_URL`       | Postgres de produção (direto ou pooler em modo session)                    |
| `AUTH_URL`           | URL pública do web, igual ao `BETTER_AUTH_URL`                             |
| `CORS_ORIGINS`       | `["https://<url-do-web>"]`                                                 |
| `SERVICE_API_KEYS`   | se houver chamadas servidor-a-servidor                                     |

### Caddy e SSE

O `Caddyfile` foi escrito para não quebrar o streaming:

- **Sem `encode`**: compressão faz o proxy segurar o stream em buffer.
- **`flush_interval -1`**: repassa cada evento imediatamente.
- **`read_timeout 10m`**: runs longos não são cortados pelo proxy. O limite real é o `RUN_TIMEOUT_SECONDS` do agent.

O agent também manda `X-Accel-Buffering: no` e um ping SSE a cada 15 s, para o caso de outro proxy na frente.

## Web (Vercel)

- Root directory: `apps/web`. O Vercel detecta o pnpm pelo `packageManager`.
- Variáveis: `DATABASE_URL`, `BETTER_AUTH_SECRET` (gere um novo, não reaproveite o de dev), `BETTER_AUTH_URL` (URL pública do web) e `NEXT_PUBLIC_AGENT_URL`.
- O build falha sem as variáveis do servidor (`src/utils/env.ts` valida ao carregar a rota de auth). Isso é proposital.
- Trocar o `BETTER_AUTH_SECRET` em produção invalida as chaves do JWT e as sessões; veja [`autenticacao.md`](./autenticacao.md#regras-que-quebram-em-silêncio).

## Antes de abrir para o público

- **Rate limit por usuário**: o custo do LLM é o risco real. Ainda não existe.
- **Runs longos ou que sobrevivam à desconexão**: hoje o run morre junto com a conexão SSE. Para isso, seria preciso um worker (ex.: arq + Redis).
- **Ferramentas reais**: `send_email` não envia nada (há um `TODO` em `graph/tools.py`).
