from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from psycopg_pool import AsyncConnectionPool


class ThreadBusy(Exception):
    pass


@asynccontextmanager
async def thread_run_lock(pool: AsyncConnectionPool, thread_id: UUID) -> AsyncIterator[None]:
    """Garante 1 run por thread, entre réplicas.

    Session-level advisory lock: segura uma conexão do pool durante o run.
    Dimensione DB_POOL_MAX acima do número de runs concorrentes por réplica.
    Se a conexão cair, o Postgres libera o lock sozinho.
    """
    key = str(thread_id)
    async with pool.connection() as conn:
        cur = await conn.execute(
            "select pg_try_advisory_lock(hashtextextended(%s, 0)) as locked", (key,)
        )
        row = await cur.fetchone()
        if not row or not row["locked"]:
            raise ThreadBusy(key)
        try:
            yield
        finally:
            await conn.execute("select pg_advisory_unlock(hashtextextended(%s, 0))", (key,))
