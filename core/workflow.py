"""
Builds the search -> extract -> validate -> (retry | end) graph for any
UseCaseConfig. This file is identical for every use case.
"""
import langgraph.graph as graph  
from langgraph.graph import StateGraph, END 

from core.contracts import UseCaseConfig, GraphState
from core.nodes import make_search_node, make_extract_node, make_validate_node, route_after_validate


def build_graph(config: UseCaseConfig):
    graph = StateGraph(GraphState)

    graph.add_node("search", make_search_node(config))
    graph.add_node("extract", make_extract_node(config))
    graph.add_node("validate", make_validate_node(config))

    graph.set_entry_point("search")
    graph.add_edge("search", "extract")
    graph.add_edge("extract", "validate")
    graph.add_conditional_edges(
        "validate", route_after_validate, {"search": "search", "end": END}
    )

    return graph.compile()
