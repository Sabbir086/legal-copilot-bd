from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


DocumentStatus = Literal[
    "queued", "processing", "partial", "completed", "failed", "needs_ocr", "ocr_unavailable"
]
DocumentType = Literal[
    "contract", "court_filing", "court_order", "legal_notice", "statute",
    "correspondence", "identity_supporting_evidence", "other", "land_record", "deed",
]


class EvidenceLocator(BaseModel):
    model_config = ConfigDict(extra="allow")
    kind: str
    page_number: int | None = None
    paragraph_index: int | None = None
    table_index: int | None = None
    row_index: int | None = None
    cell_index: int | None = None
    block_index: int | None = None
    section_heading: str | None = None
    clause_number: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None


class EvidenceFact(BaseModel):
    field: str
    value: str | None = None
    evidence_locator: EvidenceLocator | dict[str, Any]
    supporting_quote: str | None = None
    confidence: float = Field(ge=0, le=1)
    extraction_method: Literal["rule_based", "ocr_rule_based", "llm", "manual"]
    needs_review: bool = False
    uncertainty_reason: str | None = None


class ClassificationEvidence(BaseModel):
    evidence_locator: EvidenceLocator | dict[str, Any]
    quote: str
    matched_rule: str


class DocumentClassification(BaseModel):
    document_type: DocumentType
    confidence: float = Field(ge=0, le=1)
    method: str = "rule_based"
    evidence: list[ClassificationEvidence] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    attempts: int = 0
    error_code: str | None = None
    error_message: str | None = None
    updated_at: str | None = None


class DocumentAnalysisResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus
    document_type: str | None = None
    classification_confidence: float | None = None
    summary: str | None = None
    language: str = "auto"
    page_count: int = 0
    extracted_characters: int = 0
    facts: list[EvidenceFact] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    prompt_injection_detected: bool = False
    prompt_injection: dict[str, Any] = Field(default_factory=dict)
    omitted_context: dict[str, Any] = Field(default_factory=dict)


class PaginatedResponse(BaseModel):
    items: list[dict[str, Any]]
    limit: int
    offset: int
    total: int


class DocumentDetailsResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus
    document_type: str | None = None
    summary: str | None = None
    page_count: int = 0
    extracted_characters: int = 0
    job: dict[str, Any] | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None


class DocumentRetryResponse(BaseModel):
    document_id: str
    status: Literal["queued"]
    job_id: str
    message: str
