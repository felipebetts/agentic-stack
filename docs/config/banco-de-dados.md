# Banco de dados (Postgres)

Um único Postgres atende os dois apps, cada um no seu schema. Não há ORM: o agent usa `psycopg` direto (mais o checkpointer do LangGraph), e o web usa o adapter `pg`/Kysely do próprio Better Auth.

## Schemas e tabelas

| Schema   | Dono  | Tabelas                                                                                          | Criadas por                               |
| -------- | ----- | ------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| `agent`  | agent | `agent_threads`, `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations` | API do agent, no startup                  |
| `auth`   | web   | `user`, `session`, `account`, `verification`, `jwks`                                             | `pnpm auth:migrate` / `make auth-migrate` |
| `public` | —     | vazio                                                                                            | —                                         |

- **`agent_threads`**: metadados e posse das conversas (`id`, `user_id`, `title`, `created_at`, `updated_at`). O conteúdo da conversa fica nos checkpoints.
- **`checkpoint*`**: tabelas do `AsyncPostgresSaver` do LangGraph; guardam o estado do grafo a cada passo (é isso que permite pausar num interrupt e retomar depois).
- **`auth.*`**: tabelas padrão do Better Auth; `jwks` guarda o par de chaves do plugin `jwt` (ver [`autenticacao.md`](./autenticacao.md)).

Nenhum app lê o schema do outro. O vínculo entre eles é só lógico: `agent_threads.user_id` contém o `id` de `auth.user` (via `sub` do JWT), sem foreign key. Isso mantém o agent independente do provedor de login.

## `search_path` fixado nos dois apps

O `search_path` padrão do Postgres é `"$user", public`. Com o usuário de dev chamado `agent`, igual ao schema do agent, tabelas sem schema explícito caem em `agent`. Isso já aconteceu com as tabelas do Better Auth. Por isso os dois apps fixam o próprio schema na conexão:

- **agent**: `persistence/pool.py` roda `set search_path to <DB_SCHEMA>, public` em toda conexão nova.
- **web**: `src/lib/auth.ts` abre o pool com `options: '-c search_path=auth'`.

Também é por isso que as tabelas não ficam em `public`: em hospedagens que expõem `public` por API automática (ex.: PostgREST), elas ficariam acessíveis por fora.

## Migrações

**Agent** (`persistence/migrations.py`), automáticas a cada startup:

1. Pega um advisory lock fixo (`7310001`), para várias réplicas subindo juntas não competirem.
2. `create schema if not exists agent`.
3. `checkpointer.setup()` (tabelas do LangGraph; usa `CREATE INDEX CONCURRENTLY`, por isso a conexão é `autocommit`).
4. `create table if not exists agent_threads` + índice `(user_id, updated_at desc)`.

**Web** (`pnpm auth:migrate`), manual e idempotente:

1. `scripts/ensure-auth-schema.mjs` cria o schema `auth`. Sem `DATABASE_URL`, para com uma mensagem clara (o `pg` sozinho daria um erro de SASL que não explica nada).
2. `auth migrate --config src/lib/auth.ts --yes` (CLI oficial do Better Auth, pacote `auth`) cria ou atualiza as tabelas.

O passo 1 é obrigatório: a CLI descobre o schema por `current_schema()`. Se o schema do `search_path` não existe, ela **cria as tabelas em `public` sem avisar**.

Rode `pnpm auth:migrate` contra produção antes do primeiro deploy do web e sempre que atualizar o Better Auth. Em dev, `make dev` já roda.

## Conexões e pool (agent)

`persistence/pool.py` cria um `AsyncConnectionPool` compartilhado por checkpointer, tabela de threads e locks:

- `DB_POOL_MIN=1`, `DB_POOL_MAX=20`.
- `autocommit=True` (exigido pelo `setup()` do checkpointer), `row_factory=dict_row`.
- `prepare_threshold=0`: desliga prepared statements, que quebram atrás de poolers.

## Um run por thread (advisory lock)

`persistence/locks.py` usa `pg_try_advisory_lock(hashtextextended(thread_id, 0))` numa conexão do pool e **segura essa conexão durante o run inteiro**. Consequências:

- Vale entre réplicas (o lock é no Postgres), então dá para escalar o agent horizontalmente.
- Se o processo cair, o Postgres libera o lock junto com a conexão.
- **Dimensione `DB_POOL_MAX` acima do número de runs simultâneos por réplica**: cada run ocupa uma conexão.
- **Pooler em modo transaction não funciona** (ex.: porta 6543 do Supavisor/PgBouncer em modo transaction): o lock de sessão se perde entre transações. Use conexão direta ou pooler em modo session.

## Dev local

- `docker-compose.yml` sobe `postgres:16` com usuário, senha e banco `agent`, porta 5432, volume `pgdata`.
- `make db` espera o healthcheck (`--wait`).
- Acesso rápido:

  ```bash
  docker compose exec postgres psql -U agent
  ```

- **Ao limpar dados de teste, filtre pelo usuário**. Conversas criadas com `AUTH_DISABLED` pertencem a `dev-user`. Apagar `agent.agent_threads` sem filtro remove a posse de conversas que ainda têm checkpoints (a thread some da lista, mas o conteúdo continua lá).
- Apagar uma thread pela API (`DELETE /v1/threads/{id}`) remove a linha e os checkpoints juntos.
