from psycopg import AsyncConnection, sql
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from agent.config import Settings


def create_pool(s: Settings) -> AsyncConnectionPool:
    """Pool compartilhado entre checkpointer, tabela de threads e locks.

    O search_path aponta para um schema próprio, separado das tabelas do Better Auth
    (que ficam em `public`).
    """
    schema = sql.Identifier(s.db_schema)

    async def configure(conn: AsyncConnection) -> None:
        await conn.execute(sql.SQL("set search_path to {}, public").format(schema))

    return AsyncConnectionPool(
        conninfo=s.database_url,
        min_size=s.db_pool_min,
        max_size=s.db_pool_max,
        open=False,
        configure=configure,
        # autocommit é exigido pelo setup() do checkpointer (CREATE INDEX CONCURRENTLY)
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
