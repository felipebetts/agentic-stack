# Autenticação (Better Auth + JWT entre web e agent)

Postgres puro + [Better Auth](https://www.better-auth.com), sem serviço externo. O web cuida de login e sessão; o agent só confia em JWTs assinados pelo web. Não há sessão nem cookie compartilhado entre os dois.

## Fluxo

```
browser ──login (cookie)──▶ web /api/auth/*  ──▶ Postgres, schema auth (user, session, jwks…)
   │                            │
   │  GET /api/auth/token       │ JWKS público em /api/auth/jwks
   ▼                            ▼
 JWT EdDSA (15 min) ──Bearer──▶ agent: valida assinatura (JWKS), iss/aud = AUTH_URL, exp
                                 `sub` = id do usuário = dono das threads
```

1. O usuário entra com email e senha. O Better Auth grava a sessão no schema `auth` e devolve um cookie para o domínio do web.
2. Antes de chamar o agent, o front pede `GET /api/auth/token`, que exige a sessão (cookie) e devolve um JWT de 15 minutos.
3. O front manda `Authorization: Bearer <jwt>` para o agent, que valida e usa o `sub` como `user_id`.

Por que JWT em vez de o agent ler a sessão do banco: o web (Vercel) e o agent (VPS) ficam em domínios diferentes, então cookie compartilhado não funciona. E assim o agent não depende das tabelas do Better Auth: ele só precisa da chave pública.

## Lado do web

- **Config**: `apps/web/src/lib/auth.ts` (`betterAuth`, `emailAndPassword`, plugins `jwt()` e `nextCookies()`). As rotas ficam em `src/app/api/auth/[...all]/route.ts`.
- **Plugin `jwt`**: assina com EdDSA (Ed25519) por padrão, com `iss` e `aud` iguais ao `BETTER_AUTH_URL`, e expõe `GET /api/auth/jwks`. O par de chaves fica na tabela `auth.jwks`, com a chave privada **criptografada com o `BETTER_AUTH_SECRET`**.
- **Cache do token no cliente**: `src/lib/agent/instance.ts` reaproveita o JWT até faltar 1 minuto para expirar e o descarta no "Sair".
- **Página protegida**: `src/app/page.tsx` lê a sessão no servidor e decide entre a tela de login e o chat.
- **Tabelas**: criadas por `pnpm auth:migrate` (ou `make auth-migrate`), no schema `auth`. Detalhes em [`banco-de-dados.md`](./banco-de-dados.md).

## Lado do agent

`apps/agent/src/agent/api/auth.py` decide o usuário de cada requisição, nesta ordem:

| Credencial                                 | Resultado                                                                     |
| ------------------------------------------ | ----------------------------------------------------------------------------- |
| `X-API-Key` válida (`SERVICE_API_KEYS`)    | Chamada servidor-a-servidor; age como o usuário em `X-User-Id` (ou `service`) |
| `X-API-Key` inválida                       | 401                                                                           |
| `Authorization: Bearer <jwt>`              | Valida o JWT; `user_id = sub`                                                 |
| Nada, com `AUTH_DISABLED=true` e `ENV=dev` | Usuário `dev-user` (para `/docs` e curl)                                      |
| Nada                                       | 401 `credenciais ausentes`                                                    |

A validação do JWT (`JwtVerifier`):

- **Algoritmos aceitos**: só assimétricos (`EdDSA`, `ES256`, `ES512`, `PS256`, `RS256`). HS256 é recusado antes de buscar chave: como a chave vem de um JWKS público, aceitar HMAC abriria ataque de _alg confusion_.
- **Chave**: buscada no JWKS (`PyJWKClient`, cache de 10 min, rebusca quando aparece um `kid` novo).
- **Claims**: assinatura, `exp` e `sub` obrigatórios, `iss` e `aud` iguais a `AUTH_URL`.

Variáveis:

| Variável           | Para quê                                                                                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AUTH_URL`         | URL pública do web. Vira o `iss`/`aud` esperado e a base do JWKS (`{AUTH_URL}/api/auth/jwks`)                                                                       |
| `AUTH_JWKS_URL`    | Opcional: outro endereço para buscar o JWKS quando o agent alcança o web por outra rede (ex.: `host.docker.internal` no `make up`). Não muda o `iss`/`aud` esperado |
| `SERVICE_API_KEYS` | Lista JSON de chaves para servidor-a-servidor                                                                                                                       |
| `AUTH_DISABLED`    | Só em `ENV=dev`. Tokens enviados continuam sendo validados; só a ausência de credencial vira `dev-user`                                                             |

## Regras que quebram em silêncio

- **`AUTH_URL` (agent) ≠ `BETTER_AUTH_URL` (web)**: todo token é recusado (`iss`/`aud` inválidos) e o chat dá 401.
- **Trocar o `BETTER_AUTH_SECRET`**: a chave privada em `auth.jwks` não abre mais e toda página dá 500 com `Failed to decrypt private key`. Apague as chaves e o Better Auth cria outras na próxima requisição:

  ```bash
  docker compose exec postgres psql -U agent -c 'delete from auth.jwks'
  ```

  As sessões abertas também deixam de valer (o segredo assina os cookies); os usuários entram de novo.

- **Sem `BETTER_AUTH_SECRET` em produção**: o Better Auth recusa o segredo padrão e o app não sobe.
- **`CORS_ORIGINS` sem a URL do web**: o navegador bloqueia as chamadas ao agent.

## Testes

`apps/agent/tests/test_auth.py` gera um par Ed25519, monta um JWKS falso e valida tokens no formato do Better Auth, sem rede: aceita o válido e recusa `aud` errado, `iss` errado, expirado, assinado por outra chave e HS256.
