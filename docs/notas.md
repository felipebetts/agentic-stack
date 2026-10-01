# Notas e decisões do projeto

Registro cronológico de decisões, aprendizados e mudanças não óbvias do projeto como um todo, que não cabem em nenhum doc de `docs/config/` (esses são organizados por área, não por data). Serve de memória entre sessões: antes de investigar algo do zero, olhe aqui. Decisões só do front ficam em [`apps/web/docs/notas.md`](../apps/web/docs/notas.md).

Formato de cada entrada: data, o que mudou ou foi decidido, e o porquê (quando relevante).

## Como usar

- Ao tomar uma decisão não óbvia, descobrir uma restrição ou fazer uma mudança que outra sessão precisaria redescobrir, adicione uma entrada aqui (ou atualize o `docs/config/*.md` da área, se for sobre como uma parte do stack está configurada).
- Entradas que não valem mais (decisão revertida, contexto que deixou de existir) devem ser removidas ou marcadas como obsoletas, não acumuladas indefinidamente.

## Entradas

- **2026-10-01** — Autenticação trocada de Supabase Auth para Better Auth sobre Postgres puro: nenhum serviço externo além do banco. O agent continua validando JWT por JWKS, agora o do plugin `jwt` do Better Auth (`/api/auth/jwks`). HS256 deixou de ser aceito (chave vinda de JWKS público + HMAC = risco de _alg confusion_). Ver [`config/autenticacao.md`](./config/autenticacao.md).
- **2026-10-01** — Tabelas do Better Auth num schema próprio, `auth`, separado do `agent`. Sem `search_path` fixo, o padrão `"$user", public` mandava as tabelas para o schema `agent` (o usuário de dev se chama `agent`). E a CLI do Better Auth cai em `public` sem avisar se o schema não existe; por isso o `auth:migrate` cria o schema antes. Ver [`config/banco-de-dados.md`](./config/banco-de-dados.md).
- **2026-10-01** — `AUTH_URL` (claims esperados) separado de `AUTH_JWKS_URL` (onde buscar as chaves): de dentro de um container o agent alcança o web por `host.docker.internal`, mas o `iss`/`aud` do token continua sendo a URL pública.
- **2026-10-01** — Front reescrito a partir do template `felipebetts/nextjs-16-boilerplate` (Next 16, pnpm, Tailwind v4 + shadcn/ui, Vitest + Playwright), substituindo o app antigo (Next 15, npm, CSS puro). O novo ficou em `apps/web`, no mesmo caminho, para não mudar Makefile, CI nem o root directory do Vercel. O chat usa os componentes `message`/`message-scroller`/`bubble`/`marker` do shadcn.
- **2026-10-01** — `make dev` passou a fazer `env-check` antes de tudo. Sem `apps/web/.env.local`, o `pg` conectava sem senha e o erro era um `SASL: client password must be a string`, que não dizia o que faltava.
- **2026-10-01** — Chaves do JWT ficam em `auth.jwks` criptografadas com o `BETTER_AUTH_SECRET`. Trocar o segredo (inclusive de um ambiente de teste para o real) quebra todas as páginas com `Failed to decrypt private key` até as chaves serem apagadas. Ver [`config/autenticacao.md`](./config/autenticacao.md#regras-que-quebram-em-silêncio).
- **2026-10-01** — Para ver a UI sem chave do OpenRouter, dá para subir a API com o `GenericFakeChatModel` no lugar do LLM (como nos testes), desde que com `disable_streaming=True`: em streaming ele descarta os tool calls.
- **2026-10-01** — Ainda não há repositório git. O CI (`.github/workflows/agent.yml`), o `make check-contract` e os hooks do Husky pressupõem que a raiz deste monorepo será a raiz do repositório.
