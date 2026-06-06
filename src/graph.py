from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.nodes.calculate_benefit import calculate_benefit_node
from src.nodes.check_medical import check_medical_node
from src.nodes.generate_report import generate_report_node
from src.nodes.lookup_policy import lookup_policy_node
from src.nodes.set_recommendation import set_approve, set_reject, set_request_more_info
from src.nodes.verify_documents import verify_documents_node
from src.routing.conditions import (
    route_after_benefit,
    route_after_documents,
    route_after_medical,
    route_after_policy,
)
from src.state import ClaimAssessmentState


def build_graph() -> StateGraph:
    graph = StateGraph(ClaimAssessmentState)

    # Add nodes
    graph.add_node("lookup_policy", lookup_policy_node)
    graph.add_node("verify_documents", verify_documents_node)
    graph.add_node("check_medical", check_medical_node)
    graph.add_node("calculate_benefit", calculate_benefit_node)
    graph.add_node("set_approve", set_approve)
    graph.add_node("set_reject", set_reject)
    graph.add_node("set_request_more_info", set_request_more_info)
    graph.add_node("generate_report", generate_report_node)

    # Entry
    graph.add_edge(START, "lookup_policy")

    # Conditional routing
    graph.add_conditional_edges(
        "lookup_policy",
        route_after_policy,
        ["verify_documents", "set_reject"],
    )
    graph.add_conditional_edges(
        "verify_documents",
        route_after_documents,
        ["check_medical", "set_request_more_info"],
    )
    graph.add_conditional_edges(
        "check_medical",
        route_after_medical,
        ["calculate_benefit", "set_reject"],
    )
    graph.add_conditional_edges(
        "calculate_benefit",
        route_after_benefit,
        ["set_approve", "set_reject"],
    )

    # Terminal nodes → generate report → END
    graph.add_edge("set_approve", "generate_report")
    graph.add_edge("set_reject", "generate_report")
    graph.add_edge("set_request_more_info", "generate_report")
    graph.add_edge("generate_report", END)

    return graph


def compile_agent():
    graph = build_graph()
    return graph.compile()
