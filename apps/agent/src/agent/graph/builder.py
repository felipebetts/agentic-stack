from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.graph.prompts import SYSTEM_PROMPT
from agent.graph.state import AgentState
from agent.graph.tools import TOOLS
from agent.llm import get_llm

# Nós cujos tokens são enviados ao cliente via SSE.
STREAMING_NODES = frozenset({"agent"})


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    llm: BaseChatModel | None = None,
) -> CompiledStateGraph:
    model = (llm or get_llm()).bind_tools(TOOLS)

    async def agent(state: AgentState, config: RunnableConfig) -> dict:
        messages = [SystemMessage(SYSTEM_PROMPT), *state["messages"]]
        response = await model.ainvoke(messages, config)
        return {"messages": [response]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=checkpointer, name="agent")
