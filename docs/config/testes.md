# Testes e CI

Cada app tem sua suíte; o `Makefile` e o workflow do GitHub as rodam juntas. Os detalhes de configuração do Vitest e do Playwright estão em [`apps/web/docs/config/testes.md`](../../apps/web/docs/config/testes.md).

## Visão geral

| Suíte                  | Onde                       | Rede/banco?                       | Comando                          |
| ---------------------- | -------------------------- | --------------------------------- | -------------------------------- |
| Agent (pytest)         | `apps/agent/tests/`        | Não                               | `cd apps/agent && uv run pytest` |
| Web unitários (Vitest) | `apps/web/src/tests/unit/` | Não                               | `cd apps/web && pnpm test`       |
| Web E2E (Playwright)   | `apps/web/src/tests/e2e/`  | Sobe build de produção em `:3100` | `cd apps/web && pnpm test:e2e`   |
| Typecheck do web       | —                          | Não                               | `cd apps/web && pnpm typecheck`  |

`make test` roda pytest + typecheck + Vitest. `make lint` roda ruff (check e format) + ESLint. O E2E fica de fora dos dois, porque faz build completo e roda em três navegadores.

## Agent (pytest)

Config em `pyproject.toml` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`). `tests/conftest.py` define `OPENROUTER_API_KEY` e `DATABASE_URL` falsos, só para o `Settings` carregar.

- **`test_graph.py`**: monta o grafo real com um LLM falso (`GenericFakeChatModel` com `bind_tools` neutralizado) e `InMemorySaver`, e percorre o fluxo pelo mesmo `stream_run` da API: tool call de `send_email` → evento `interrupt` → `Command(resume={"approved": True})` → tool executa → resposta final. Valida a tradução para eventos SSE sem HTTP, rede nem Postgres.
- **`test_auth.py`**: valida JWTs no formato do Better Auth com um JWKS falso (ver [`autenticacao.md`](./autenticacao.md#testes)).

Limitação conhecida do `GenericFakeChatModel`: em modo streaming ele **descarta os tool calls** e falha com mensagens sem texto. Para simular tools, use `disable_streaming=True` (como em `test_graph.py`).

O que não tem teste automatizado: rotas HTTP com Postgres real (locks, posse, migrations) e o LLM real.

## Web

- **Unitários**: parser SSE (`sse.test.ts`), estado do chat (`chat-state.test.ts`) e cartão de aprovação (`approval-card.test.tsx`).
- **E2E**: visitante sem sessão vê a tela de login. Precisa de `DATABASE_URL`, `BETTER_AUTH_SECRET` e `BETTER_AUTH_URL` no ambiente (ou no `.env.local`), porque o build carrega a rota de auth. Os navegadores do Playwright precisam estar instalados (`pnpm exec playwright install`).
- **`pnpm typecheck`** roda `next typegen` antes do `tsc`; sem isso, tipos gerados pelo Next (`LayoutProps`) não existem num clone limpo.

## CI (`.github/workflows/agent.yml`)

Roda em push para `main` e em PRs que mexem em `apps/agent/**` ou `apps/web/**`.

**Job `test`**:

1. `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest` (agent).
2. `pnpm install --frozen-lockfile` (web; pnpm e Node vêm de `package.json#packageManager` e `.nvmrc`).
3. `make check-contract`: falha se `openapi.json` ou `schema.d.ts` não batem com o código.
4. `pnpm lint`, `pnpm typecheck`, `pnpm test` (web).

**Job `image`** (só push na `main`, depois do `test`): build da imagem do agent e push para o GHCR. Ver [`deploy.md`](./deploy.md).

O E2E não roda no CI hoje.

O workflow pressupõe que a raiz deste monorepo é a raiz do repositório git. Se o repo ficar num diretório acima, os caminhos `apps/...` e o próprio `.github/` deixam de valer.

## Git hooks

O web tem Husky (`pre-commit`: lint-staged; `pre-push`: `pnpm test`), instalado pelo `prepare` do `apps/web/package.json`, que aponta o Husky para `apps/web/.husky` a partir da raiz do repo. Só passa a valer depois de um `git init` na raiz e de um novo `pnpm install`. Detalhes em [`apps/web/docs/config/husky.md`](../../apps/web/docs/config/husky.md).
