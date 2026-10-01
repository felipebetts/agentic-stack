import asyncio
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from psycopg_pool import AsyncConnectionPool
from sse_starlette import EventSourceResponse

from agent.api.auth import Principal
from agent.api.deps import GraphDep, PoolDep, PrincipalDep, SettingsDep, ThreadDep
from agent.api.schemas import ErrorEvent, ErrorOut, ResumeIn, RunIn, ThreadStateOut
from agent.api.serializers import load_thread_state
from agent.api.streaming import stream_run
from agent.config import Settings
from agent.observability import get_callbacks
from agent.persistence.locks import ThreadBusy, thread_run_lock
from agent.persistence.threads import touch_thread

router = APIRouter(prefix="/threads/{thread_id}/runs", tags=["runs"])

SSE_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Stream SSE. Cada evento tem `event:` igual ao campo `event` do payload.",
        "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/StreamEvent"}}},
    },
    409: {"model": ErrorOut},
}


def _run_config(s: Settings, thread_id: UUID, principal: Principal, run_id: UUID) -> RunnableConfig:
    return {
        "run_id": run_id,
        "recursion_limit": s.recursion_limit,
        "callbacks": get_callbacks(),
        "configurable": {"thread_id": str(thread_id), "user_id": principal.user_id},
        "metadata": {"langfuse_session_id": str(thread_id), "langfuse_user_id": principal.user_id},
    }


async def _assert_interrupt_state(graph: CompiledStateGraph, thread_id: UUID, *, pending: bool):
    snapshot = await graph.aget_state({"configurable": {"thread_id": str(thread_id)}})
    has_pending = bool(snapshot.interrupts)
    if pending and not has_pending:
        raise HTTPException(409, {"code": "no_pending_interrupt", "message": "nada para retomar"})
    if not pending and has_pending:
        raise HTTPException(
            409,
            {"code": "pending_interrupt", "message": "responda o interrupt pendente via /resume"},
        )


def _sse(
    *,
    s: Settings,
    pool: AsyncConnectionPool,
    graph: CompiledStateGraph,
    graph_input: Any,
    config: RunnableConfig,
    thread_id: UUID,
    run_id: UUID,
    title_hint: str | None,
) -> EventSourceResponse:
    async def events():
        try:
            async with thread_run_lock(pool, thread_id):
                async for ev in stream_run(
                    graph,
                    graph_input,
                    config,
                    run_id=str(run_id),
                    thread_id=str(thread_id),
                    max_seconds=s.run_timeout_seconds,
                ):
                    yield {"event": ev.event, "data": ev.model_dump_json()}
                await touch_thread(pool, thread_id, title_hint)
        except ThreadBusy:
            ev = ErrorEvent(code="thread_busy", message="já existe um run nesta thread")
            yield {"event": ev.event, "data": ev.model_dump_json()}

    return EventSourceResponse(events(), ping=15, headers={"X-Accel-Buffering": "no"})


@router.post("/stream", responses=SSE_RESPONSES)
async def stream(
    body: RunIn,
    thread: ThreadDep,
    principal: PrincipalDep,
    graph: GraphDep,
    pool: PoolDep,
    s: SettingsDep,
):
    thread_id, run_id = thread["id"], uuid4()
    await _assert_interrupt_state(graph, thread_id, pending=False)
    return _sse(
        s=s,
        pool=pool,
        graph=graph,
        graph_input={"messages": [HumanMessage(content=body.message)]},
        config=_run_config(s, thread_id, principal, run_id),
        thread_id=thread_id,
        run_id=run_id,
        title_hint=body.message,
    )


@router.post("/resume", responses=SSE_RESPONSES)
async def resume(
    body: ResumeIn,
    thread: ThreadDep,
    principal: PrincipalDep,
    graph: GraphDep,
    pool: PoolDep,
    s: SettingsDep,
):
    thread_id, run_id = thread["id"], uuid4()
    await _assert_interrupt_state(graph, thread_id, pending=True)
    value = {body.interrupt_id: body.value} if body.interrupt_id else body.value
    return _sse(
        s=s,
        pool=pool,
        graph=graph,
        graph_input=Command(resume=value),
        config=_run_config(s, thread_id, principal, run_id),
        thread_id=thread_id,
        run_id=run_id,
        title_hint=None,
    )


@router.post(
    "/wait",
    response_model=ThreadStateOut,
    responses={409: {"model": ErrorOut}, 504: {"model": ErrorOut}},
)
async def wait(
    body: RunIn,
    thread: ThreadDep,
    principal: PrincipalDep,
    graph: GraphDep,
    pool: PoolDep,
    s: SettingsDep,
):
    """Execução síncrona, para consumidores que não querem lidar com SSE."""
    thread_id = thread["id"]
    await _assert_interrupt_state(graph, thread_id, pending=False)
    config = _run_config(s, thread_id, principal, uuid4())
    try:
        async with thread_run_lock(pool, thread_id):
            async with asyncio.timeout(s.run_timeout_seconds):
                await graph.ainvoke({"messages": [HumanMessage(content=body.message)]}, config)
            await touch_thread(pool, thread_id, body.message)
    except ThreadBusy as e:
        raise HTTPException(409, {"code": "thread_busy", "message": "run em andamento"}) from e
    except TimeoutError as e:
        raise HTTPException(504, {"code": "timeout", "message": "run excedeu o limite"}) from e
    return await load_thread_state(graph, thread_id)
