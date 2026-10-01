"""Metadados de thread e posse (user_id). O estado em si fica no checkpointer."""

from typing import Any
from uuid import UUID, uuid4

from psycopg_pool import AsyncConnectionPool

_SCHEMA = (
    """
    create table if not exists agent_threads (
      id uuid primary key,
      user_id text not null,
      title text,
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now()
    )
    """,
    "create index if not exists agent_threads_user_idx on agent_threads (user_id, updated_at desc)",
)

_COLS = "id, title, created_at, updated_at"


async def ensure_schema(pool: AsyncConnectionPool) -> None:
    async with pool.connection() as conn:
        for stmt in _SCHEMA:
            await conn.execute(stmt)


async def create_thread(pool: AsyncConnectionPool, user_id: str, title: str | None) -> dict:
    async with pool.connection() as conn:
        cur = await conn.execute(
            f"insert into agent_threads (id, user_id, title) values (%s, %s, %s) returning {_COLS}",
            (uuid4(), user_id, title),
        )
        return await cur.fetchone()  # type: ignore[return-value]


async def get_thread(pool: AsyncConnectionPool, thread_id: UUID, user_id: str) -> dict | None:
    async with pool.connection() as conn:
        cur = await conn.execute(
            f"select {_COLS} from agent_threads where id = %s and user_id = %s",
            (thread_id, user_id),
        )
        return await cur.fetchone()


async def list_threads(pool: AsyncConnectionPool, user_id: str, limit: int) -> list[dict[str, Any]]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            f"select {_COLS} from agent_threads where user_id = %s "
            "order by updated_at desc limit %s",
            (user_id, limit),
        )
        return await cur.fetchall()


async def touch_thread(pool: AsyncConnectionPool, thread_id: UUID, title_hint: str | None) -> None:
    title = title_hint.strip()[:80] if title_hint else None
    async with pool.connection() as conn:
        await conn.execute(
            "update agent_threads set updated_at = now(), title = coalesce(title, %s) "
            "where id = %s",
            (title, thread_id),
        )


async def delete_thread(pool: AsyncConnectionPool, thread_id: UUID) -> None:
    async with pool.connection() as conn:
        await conn.execute("delete from agent_threads where id = %s", (thread_id,))
