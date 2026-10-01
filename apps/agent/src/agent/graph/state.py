from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Estado do grafo. Adicione campos aqui (ex.: plan, scratchpad, user_profile).

    Tudo que estiver aqui é persistido pelo checkpointer a cada step.
    """
