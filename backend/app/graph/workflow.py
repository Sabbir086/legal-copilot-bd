"""Minimal LangGraph orchestration for document risk screening.

The current graph contains detection and document-evidence validation nodes.
Legal retrieval, statute verification and memorandum review are intentionally
not represented as completed nodes yet.
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.risk_agent import detect_with_openrouter_or_fallback, verify_document_evidence
from app.schemas.legal import RiskFinding


class AnalysisState(TypedDict):
    pages: list[dict]
    findings: list[RiskFinding]
    analysis_method: str
    analysis_notice: str | None


async def detect_node(state: AnalysisState) -> dict:
    findings, method, notice = await detect_with_openrouter_or_fallback(state["pages"])
    return {
        "findings": findings,
        "analysis_method": method,
        "analysis_notice": notice,
    }


def evidence_validation_node(state: AnalysisState) -> dict:
    validated = verify_document_evidence(state["findings"], state["pages"])
    return {"findings": validated}


def build_analysis_graph():
    builder = StateGraph(AnalysisState)
    builder.add_node("risk_detection", detect_node)
    builder.add_node("document_evidence_validation", evidence_validation_node)
    builder.add_edge(START, "risk_detection")
    builder.add_edge("risk_detection", "document_evidence_validation")
    builder.add_edge("document_evidence_validation", END)
    return builder.compile()


analysis_graph = build_analysis_graph()


async def analyze_pages(pages: list[dict]) -> tuple[list[RiskFinding], str, str | None]:
    result = await analysis_graph.ainvoke({
        "pages": pages,
        "findings": [],
        "analysis_method": "pending",
        "analysis_notice": None,
    })
    return result["findings"], result["analysis_method"], result["analysis_notice"]
