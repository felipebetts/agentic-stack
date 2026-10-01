from psycopg import sql
from psycopg_pool import AsyncConnectionPool

from agent.persistence.threads import ensure_schema

_MIGRATION_LOCK = 7_310_001


async def run_migrations(pool: AsyncConnectionPool, checkpointer, schema: str) -> None:
    """Cria schema + tabelas. O advisory lock evita corrida com várias réplicas subindo juntas."""
    async with pool.connection() as conn:
        await conn.execute("select pg_advisory_lock(%s)", (_MIGRATION_LOCK,))
        try:
            await conn.execute(
                sql.SQL("create schema if not exists {}").format(sql.Identifier(schema))
            )
            await checkpointer.setup()
            await ensure_schema(pool)
        finally:
            await conn.execute("select pg_advisory_unlock(%s)", (_MIGRATION_LOCK,))
