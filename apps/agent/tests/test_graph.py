"""Testa grafo + tradução de eventos sem rede e sem Postgres."""

from typing import Any

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agent.api.schemas import DoneEvent, InterruptEvent, MessageEvent
from agent.api.streaming import stream_run
from agent.graph.builder import build_graph


class FakeToolModel(GenericFakeChatModel):
    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolModel":
        return self


async def collect(graph, graph_input, config):
    return [
        ev
        async for ev in stream_run(
            graph, graph_input, config, run_id="r", thread_id="t", max_seconds=10
        )
    ]


async def test_interrupt_and_resume():
    llm = FakeToolModel(
        disable_streaming=True,
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "call_1",
                            "name": "send_email",
                            "args": {"to": "a@b.com", "subject": "Oi", "body": "Teste"},
                        }
                    ],
                ),
                AIMessage(content="Email enviado."),
            ]
        ),
    )
    graph = build_graph(InMemorySaver(), llm=llm)
    config = {"configurable": {"thread_id": "t1"}}

    events = await collect(graph, {"messages": [HumanMessage("manda o email")]}, config)
    interrupts = [e for e in events if isinstance(e, InterruptEvent)]
    assert len(interrupts) == 1
    assert interrupts[0].value["action"] == "send_email"
    assert isinstance(events[-1], DoneEvent) and events[-1].interrupted

    events = await collect(graph, Command(resume={"approved": True}), config)
    tool_msgs = [e for e in events if isinstance(e, MessageEvent) and e.node == "tools"]
    assert "Email enviado para a@b.com" in tool_msgs[0].message.content
    assert isinstance(events[-1], DoneEvent) and not events[-1].interrupted

    state = await graph.aget_state(config)
    assert state.values["messages"][-1].content == "Email enviado."
