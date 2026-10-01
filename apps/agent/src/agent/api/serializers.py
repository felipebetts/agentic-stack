from typing import Any
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.state import CompiledStateGraph

from agent.api.schemas import InterruptOut, MessageOut, ThreadStateOut, ToolCallOut


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        return "".join(parts)
    return ""


def serialize_message(m: BaseMessage) -> MessageOut:
    tool_calls = getattr(m, "tool_calls", None) or []
    return MessageOut(
        id=m.id,
        type=m.type,  # type: ignore[arg-type]
        content=content_to_text(m.content),
        tool_calls=[
            ToolCallOut(id=tc.get("id"), name=tc["name"], args=tc["args"]) for tc in tool_calls
        ],
        tool_call_id=getattr(m, "tool_call_id", None),
        name=m.name,
    )


def serialize_interrupt(i: Any) -> InterruptOut:
    return InterruptOut(id=getattr(i, "id", None), value=i.value)


async def load_thread_state(graph: CompiledStateGraph, thread_id: UUID) -> ThreadStateOut:
    snapshot = await graph.aget_state({"configurable": {"thread_id": str(thread_id)}})
    messages = (snapshot.values or {}).get("messages", [])
    return ThreadStateOut(
        thread_id=thread_id,
        messages=[serialize_message(m) for m in messages],
        next=list(snapshot.next),
        interrupts=[serialize_interrupt(i) for i in snapshot.interrupts],
    )
