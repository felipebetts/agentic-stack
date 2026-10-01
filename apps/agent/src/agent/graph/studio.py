"""Entry point para `langgraph dev` (LangGraph Studio).

O servidor de dev injeta o próprio checkpointer, então compilamos sem um.
Também deixa aberta a migração para o Agent Server oficial no futuro.
"""

from agent.graph.builder import build_graph

graph = build_graph()
