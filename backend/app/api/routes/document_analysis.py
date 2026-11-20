from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query

from app.services import document_store
from app.services.supabase_client import SupabaseNotConfigured
from app.schemas.document_intelligence import (
    DocumentAnalysisResponse, DocumentDetailsResponse, DocumentRetryResponse,
    DocumentStatusResponse, PaginatedResponse,
)
from app.config.settings import settings

router = APIRouter(prefix="/api/v1", tags=["document intelligence"])


def _scope(value: str | None) -> str:
    if not value:
        raise HTTPException(400, "X-Workspace-ID header is required.")
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise HTTPException(400, "Invalid workspace id.") from exc


def _document_id(value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise HTTPException(400, "Invalid document id.") from exc


def _get_document(document_id: str, workspace_id: str) -> dict:
    try:
        document = document_store.get_document_access(document_id, workspace_id)
    except SupabaseNotConfigured as exc:
        raise HTTPException(503, "Document persistence is not configured.") from exc
    except Exception as exc:
        raise HTTPException(503, "Document data could not be loaded.") from exc
    if not document:
        raise HTTPException(404, "Document not found in this workspace.")
    return document


def _page(table: str, document_id: str, workspace_id: str, limit: int, offset: int) -> dict:
    _get_document(document_id, workspace_id)
    try:
        items, total = document_store.list_document_rows(
            table, document_id, workspace_id, limit=limit, offset=offset,
        )
        if table == "document_pages":
            max_chars = settings.max_document_response_text_chars
            for item in items:
                for field in ("source_text", "ocr_text", "combined_text"):
                    original = str(item.get(field) or "")
                    if len(original) > max_chars:
                        item[field] = original[:max_chars]
                        item[f"{field}_omitted_characters"] = len(original) - max_chars
        return {"items": items, "limit": limit, "offset": offset, "total": total}
    except Exception as exc:
        raise HTTPException(503, "Document evidence could not be loaded.") from exc


@router.get("/documents/{document_id}", response_model=DocumentDetailsResponse)
def document_details(document_id: str, x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID")):
    workspace_id = _scope(x_workspace_id)
    identifier = _document_id(document_id)
    document = _get_document(identifier, workspace_id)
    try:
        job = document_store.get_document_job(identifier, workspace_id)
    except Exception as exc:
        raise HTTPException(503, "Document processing state could not be loaded.") from exc
    return {
        "document_id": identifier,
        "filename": document.get("file_name"),
        "status": document.get("processing_status", "queued"),
        "document_type": document.get("document_type"),
        "summary": document.get("summary"),
        "page_count": document.get("page_count", 0),
        "extracted_characters": document.get("extracted_characters", 0),
        "job": job,
        "last_error_code": document.get("last_error_code"),
        "last_error_message": document.get("last_error_message"),
    }


@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
def document_status(document_id: str, x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID")):
    workspace_id = _scope(x_workspace_id)
    identifier = _document_id(document_id)
    document = _get_document(identifier, workspace_id)
    job = document_store.get_document_job(identifier, workspace_id)
    return {
        "document_id": identifier,
        "status": document.get("processing_status", "queued"),
        "attempts": (job or {}).get("attempts", 0),
        "error_code": document.get("last_error_code"),
        "error_message": document.get("last_error_message"),
        "updated_at": document.get("updated_at"),
    }


@router.get("/documents/{document_id}/analysis", response_model=DocumentAnalysisResponse)
def document_analysis(document_id: str, x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID")):
    workspace_id = _scope(x_workspace_id)
    identifier = _document_id(document_id)
    _get_document(identifier, workspace_id)
    try:
        result = document_store.get_document_analysis(identifier, workspace_id)
    except Exception as exc:
        raise HTTPException(503, "Document analysis could not be loaded.") from exc
    if not result:
        raise HTTPException(404, "Document not found.")
    return result


@router.get("/documents/{document_id}/pages", response_model=PaginatedResponse)
def document_pages(
    document_id: str,
    limit: int = Query(default=25, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=100000),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
):
    return _page("document_pages", _document_id(document_id), _scope(x_workspace_id), limit, offset)


@router.get("/documents/{document_id}/segments", response_model=PaginatedResponse)
def document_segments(
    document_id: str,
    limit: int = Query(default=25, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=100000),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
):
    return _page("document_segments", _document_id(document_id), _scope(x_workspace_id), limit, offset)


@router.get("/documents/{document_id}/facts", response_model=PaginatedResponse)
def document_facts(
    document_id: str,
    limit: int = Query(default=25, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=100000),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
):
    return _page("document_facts", _document_id(document_id), _scope(x_workspace_id), limit, offset)


@router.post("/documents/{document_id}/retry", response_model=DocumentRetryResponse)
def retry_document(
    document_id: str,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
):
    workspace_id = _scope(x_workspace_id)
    identifier = _document_id(document_id)
    _get_document(identifier, workspace_id)
    try:
        job = document_store.retry_document_job(identifier, workspace_id)
    except Exception as exc:
        raise HTTPException(503, "Document retry could not be queued.") from exc
    if not job:
        raise HTTPException(409, "Document is already queued/processing or has no retryable processing job.")
    return {"document_id": identifier, "status": "queued", "job_id": job["id"], "message": "Retry queued."}
