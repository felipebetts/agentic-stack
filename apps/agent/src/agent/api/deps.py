from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from langgraph.graph.state import CompiledStateGraph
from psycopg_pool import AsyncConnectionPool

from agent.api.auth import AuthError, Principal, authenticate
from agent.config import Settings, get_settings
from agent.persistence.threads import get_thread


def get_pool(request: Request) -> AsyncConnectionPool:
    return request.app.state.pool


def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph


async def get_principal(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
) -> Principal:
    try:
        return await authenticate(
            settings,
            request.app.state.verifier,
            authorization=authorization,
            api_key=x_api_key,
            on_behalf_of=x_user_id,
        )
    except AuthError as e:
        raise HTTPException(401, detail={"code": "unauthorized", "message": str(e)}) from e


SettingsDep = Annotated[Settings, Depends(get_settings)]
PoolDep = Annotated[AsyncConnectionPool, Depends(get_pool)]
GraphDep = Annotated[CompiledStateGraph, Depends(get_graph)]
PrincipalDep = Annotated[Principal, Depends(get_principal)]


async def owned_thread(thread_id: UUID, principal: PrincipalDep, pool: PoolDep) -> dict:
    row = await get_thread(pool, thread_id, principal.user_id)
    if row is None:
        raise HTTPException(404, detail={"code": "not_found", "message": "thread não encontrada"})
    return row


ThreadDep = Annotated[dict, Depends(owned_thread)]
