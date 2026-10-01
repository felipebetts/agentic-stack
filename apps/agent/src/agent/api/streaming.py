"""Traduz o stream do LangGraph para eventos SSE tipados.

O grafo roda numa task produtora e o gerador consome de uma fila. Assim o timeout
e o cancelamento afetam só o grafo, nunca o código que está escrevendo no socket.
Se o cliente desconectar, o run é cancelado (os steps já concluídos ficam no
checkpoint). Para runs que sobrevivem a desconexão, mova a produtora para um worker.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agent.api.schemas import (
    DoneEvent,
    ErrorEvent,
    InterruptEvent,
    MessageEvent,
    RunStartedEvent,
    StreamEvent,
    TokenEvent,
)
from agent.api.serializers import content_to_text, serialize_message
from agent.graph.builder import STREAMING_NODES

log = logging.getLogger(__name__)


def _translate(mode: str, chunk: Any) -> list[StreamEvent]:
    if mode == "messages":
        message, metadata = chunk
        if metadata.get("langgraph_node") not in STREAMING_NODES:
            return []
        text = content_to_text(message.content)
        return [TokenEvent(message_id=message.id, content=text)] if text else []

    if mode == "updates":
        events: list[StreamEvent] = []
        for node, update in chunk.items():
            if node == "__interrupt__":
                events.extend(
                    InterruptEvent(interrupt_id=getattr(i, "id", None), value=i.value)
                    for i in update
                )
            elif isinstance(update, dict):
                events.extend(
                    MessageEvent(node=node, message=serialize_message(m))
                    for m in update.get("messages", [])
                )
        return events

    return []


async def stream_run(
    graph: CompiledStateGraph,
    graph_input: Any,
    config: RunnableConfig,
    *,
    run_id: str,
    thread_id: str,
    max_seconds: float,
) -> AsyncIterator[StreamEvent]:
    queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()

    async def produce() -> None:
        try:
            async with asyncio.timeout(max_seconds):
                async for mode, chunk in graph.astream(
                    graph_input, config, stream_mode=["messages", "updates"]
                ):
                    for event in _translate(mode, chunk):
                        queue.put_nowait(event)
            snapshot = await graph.aget_state(config)
            queue.put_nowait(
                DoneEvent(
                    run_id=run_id,
                    interrupted=bool(snapshot.interrupts),
                    next=list(snapshot.next),
                )
            )
        except TimeoutError:
            queue.put_nowait(ErrorEvent(code="timeout", message=f"Run excedeu {max_seconds:.0f}s"))
        except Exception:
            log.exception("run falhou", extra={"thread_id": thread_id, "run_id": run_id})
            queue.put_nowait(ErrorEvent(code="internal", message="Erro ao executar o grafo"))
        finally:
            queue.put_nowait(None)

    yield RunStartedEvent(run_id=run_id, thread_id=thread_id)
    task = asyncio.create_task(produce())
    try:
        while (event := await queue.get()) is not None:
            yield event
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
