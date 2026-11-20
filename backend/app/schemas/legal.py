from typing import Literal
from pydantic import BaseModel, Field


class RiskFinding(BaseModel):
    title: str
    category: str
    severity: Literal["critical", "high", "medium", "low"]
    clause_excerpt: str
    page: int | None = None
    explanation: str
    recommendation: str
    evidence_status: Literal["document_evidence_only", "legal_source_pending"] = "document_evidence_only"


class AnalyzeResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    analysis_method: str
    risks: list[RiskFinding] = Field(default_factory=list)
    legal_citations: list[dict] = Field(default_factory=list)
    disclaimer: str


class LegalSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    jurisdiction: str = "BD"
