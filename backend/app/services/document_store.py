from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5
from typing import Any

from app.services.supabase_client import get_supabase_client
from app.services.workspace_store import BUCKET


def _client():
    return get_supabase_client()


def _rows(response) -> list[dict[str, Any]]:
    return list(response.data or [])


def enqueue_document(*, document_id: str, attachment_id: str, workspace_id: str, conversation_id: str,
                     filename: str, storage_path: str, mime_type: str) -> None:
    document = {
        "id": document_id,
        "user_id": None,
        "workspace_id": workspace_id,
        "conversation_id": conversation_id,
        "attachment_id": attachment_id,
        "file_name": filename,
        "file_path": storage_path,
        "file_type": mime_type,
        "jurisdiction": "BD",
        "status": "uploaded",
        "processing_status": "queued",
        "last_error_code": None,
        "last_error_message": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _client().table("documents").upsert(document, on_conflict="id").execute()
    job = {
        "document_id": document_id,
        "attachment_id": attachment_id,
        "workspace_id": workspace_id,
        "conversation_id": conversation_id,
        "job_type": "extract",
        "status": "queued",
        "attempts": 0,
        "max_attempts": 3,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _client().table("document_processing_jobs").upsert(job, on_conflict="document_id,job_type").execute()



def list_documents_for_attachments(attachment_ids: list[str], workspace_id: str) -> dict[str, dict]:
    if not attachment_ids:
        return {}
    result = (
        _client().table("documents").select("id,attachment_id,processing_status")
        .in_("attachment_id", attachment_ids).eq("workspace_id", workspace_id).execute()
    )
    return {str(row["attachment_id"]): row for row in _rows(result) if row.get("attachment_id")}


def claim_next_job() -> dict | None:
    result = _client().rpc("claim_next_document_processing_job", {}).execute()
    rows = _rows(result)
    return rows[0] if rows else None


def heartbeat_job(job_id: str, workspace_id: str) -> bool:
    result = _client().rpc("heartbeat_document_processing_job", {
        "p_job_id": job_id, "p_workspace_id": workspace_id,
    }).execute()
    return bool(result.data)


def get_job_context(job: dict) -> tuple[dict, dict]:
    document_result = (
        _client().table("documents").select("id,workspace_id,conversation_id,attachment_id,file_name,file_path,file_type")
        .eq("id", job["document_id"]).eq("workspace_id", job["workspace_id"]).limit(1).execute()
    )
    documents = _rows(document_result)
    if not documents:
        raise RuntimeError("Document record is missing or workspace scope does not match.")
    document = documents[0]
    attachment_result = (
        _client().table("conversation_attachments").select("id,filename,mime_type,storage_path,workspace_id,conversation_id")
        .eq("id", document["attachment_id"]).eq("workspace_id", job["workspace_id"])
        .eq("conversation_id", job["conversation_id"]).limit(1).execute()
    )
    attachments = _rows(attachment_result)
    if not attachments:
        raise RuntimeError("Original attachment is missing or workspace scope does not match.")
    return document, attachments[0]


def download_original(storage_path: str) -> bytes:
    return _client().storage.from_(BUCKET).download(storage_path)


def upload_derived(storage_path: str, content: bytes, mime_type: str) -> None:
    _client().storage.from_(BUCKET).upload(
        path=storage_path, file=content,
        file_options={"content-type": mime_type, "upsert": "true"},
    )


def _stable_uuid(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, value))


def save_processing_result(document: dict, attachment: dict, result: dict, artifact_paths: dict[tuple[str, int | None], str]) -> None:
    document_id = document["id"]
    workspace_id = document["workspace_id"]
    conversation_id = document["conversation_id"]
    now = datetime.now(timezone.utc).isoformat()

    page_rows = []
    for index, page in enumerate(result.get("pages", []), start=1):
        page_number = page.get("page_number")
        block_index = int(page.get("block_index") or index)
        artifact_key = (page.get("artifact_type") or ("page_image" if page_number is not None else "normalized_image"), page_number if page_number is not None else block_index)
        page_rows.append({
            "id": _stable_uuid(f"m2:{document_id}:page:{page_number}:{block_index}"),
            "document_id": document_id, "workspace_id": workspace_id,
            "conversation_id": conversation_id, "page_number": page_number,
            "block_index": block_index,
            "source_text": page.get("source_text", ""), "ocr_text": page.get("ocr_text", ""),
            "combined_text": page.get("text", ""), "source_type": page.get("source_type", "source_text"),
            "ocr_status": page.get("ocr_status", "not_needed"),
            "ocr_engine": page.get("ocr_engine"), "ocr_languages": page.get("ocr_languages") or [],
            "ocr_confidence": page.get("ocr_confidence"), "image_width": page.get("image_width"),
            "image_height": page.get("image_height"), "artifact_storage_path": artifact_paths.get(artifact_key),
            "source_locator": page.get("source_locator") or {"page_number": page_number, "block_index": block_index},
            "provenance": {"source_text_kind": "selectable_text_or_docx_block", "ocr_separate_from_source": True},
            "updated_at": now,
        })
    if page_rows:
        _client().table("document_pages").upsert(page_rows, on_conflict="id").execute()

    segment_rows = []
    for segment in result.get("segments", []):
        index = int(segment["segment_index"])
        segment_id = _stable_uuid(f"m2:{document_id}:segment:{index}")
        segment_rows.append({
            "id": segment_id, "document_id": document_id, "workspace_id": workspace_id,
            "conversation_id": conversation_id, "segment_index": index,
            "parent_segment_id": (
                _stable_uuid(f"m2:{document_id}:segment:{int(segment['overlap_from_segment_index'])}")
                if segment.get("overlap") and segment.get("overlap_from_segment_index")
                else None
            ), "heading": segment.get("heading"),
            "clause_number": segment.get("clause_number"), "content": segment["text"],
            "start_locator": segment.get("start_locator", {}), "end_locator": segment.get("end_locator", {}),
            "has_overlap": bool(segment.get("overlap")),
            "overlap_from_segment_index": segment.get("overlap_from_segment_index"),
            "overlap_prefix": segment.get("overlap_prefix"),
            "character_count": int(segment.get("character_count", len(segment["text"]))),
            "updated_at": now,
        })
    if segment_rows:
        _client().table("document_segments").upsert(segment_rows, on_conflict="id").execute()

    fact_rows = []
    for fact in result.get("facts", []):
        fact_key = hashlib.sha256(json.dumps({
            "field": fact.get("field"), "locator": fact.get("evidence_locator"),
            "quote": fact.get("supporting_quote"), "value": fact.get("value"),
        }, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        fact_rows.append({
            "id": _stable_uuid(f"m2:{document_id}:fact:{fact_key}"),
            "document_id": document_id, "workspace_id": workspace_id,
            "conversation_id": conversation_id, "fact_key": fact_key,
            "field": fact["field"], "value": fact.get("value"),
            "evidence_locator": fact.get("evidence_locator", {}),
            "supporting_quote": fact.get("supporting_quote"),
            "confidence": fact.get("confidence", 0),
            "extraction_method": fact.get("extraction_method", "rule_based"),
            "needs_review": bool(fact.get("needs_review", True)),
            "uncertainty_reason": fact.get("uncertainty_reason"),
            "provenance": {"exact_quote_validated": bool(fact.get("supporting_quote"))},
            "updated_at": now,
        })
    if fact_rows:
        _client().table("document_facts").upsert(fact_rows, on_conflict="id").execute()

    classification = result.get("classification", {})
    processing_status = result.get("status", "failed")
    docs_update = {
        "processing_status": processing_status,
        "document_type": classification.get("document_type"),
        "classification_confidence": classification.get("confidence"),
        "classification_provenance": classification,
        "summary": result.get("summary"),
        "summary_provenance": result.get("summary_provenance", {}),
        "extracted_characters": int(result.get("extracted_characters", 0)),
        "page_count": int(result.get("page_count", 0)),
        "block_count": int(result.get("block_count", 0)),
        "prompt_injection_detected": bool((result.get("prompt_injection") or {}).get("detected")),
        "processing_metadata": {
            **(result.get("metadata") or {}),
            "uncertainty_notes": result.get("uncertainty_notes", []),
            "prompt_injection": result.get("prompt_injection", {}),
            "classification": classification,
        },
        "last_error_code": None if processing_status in {"completed", "partial"} else processing_status,
        "last_error_message": "; ".join(result.get("uncertainty_notes", [])) or None,
        "updated_at": now,
    }
    _client().table("documents").update(docs_update).eq("id", document_id).eq("workspace_id", workspace_id).execute()

    legacy_pages = [
        {"page": page.get("page_number"), "text": page.get("text", ""),
         "source_type": page.get("source_type", "source_text"),
         "source_locator": page.get("source_locator") or {"kind": "page" if page.get("page_number") is not None else "docx_block", "page_number": page.get("page_number"), "block_index": page.get("block_index")},
         "ocr_status": page.get("ocr_status", "not_needed")}
        for page in result.get("pages", [])
    ]
    any_text = bool(result.get("extracted_characters", 0))
    parse_status = "ready" if any_text else "failed" if processing_status == "failed" else "uploaded"
    _client().table("conversation_attachments").update({
        "document_type": classification.get("document_type", "other"),
        "document_type_bn": classification.get("document_type_bn", "অন্যান্য নথি"),
        "page_count": int(result.get("page_count", 0)),
        "extracted_characters": int(result.get("extracted_characters", 0)),
        "extracted_pages": legacy_pages,
        "parse_status": parse_status,
    }).eq("id", attachment["id"]).eq("workspace_id", workspace_id).execute()

    job_update = {
        "status": processing_status, "finished_at": now,
        "updated_at": now, "error_code": docs_update["last_error_code"],
        "error_message": docs_update["last_error_message"],
        "result_metadata": {"page_count": result.get("page_count", 0), "block_count": result.get("block_count", 0)},
    }
    _client().table("document_processing_jobs").update(job_update).eq("document_id", document_id).eq("job_type", "extract").execute()


def mark_job_failed(job: dict, error_code: str, error_message: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    update = {
        "status": "failed", "error_code": error_code[:80],
        "error_message": error_message[:1000], "finished_at": now, "updated_at": now,
    }
    _client().table("document_processing_jobs").update(update).eq("id", job["id"]).eq("workspace_id", job["workspace_id"]).execute()
    _client().table("documents").update({
        "processing_status": "failed", "last_error_code": error_code[:80],
        "last_error_message": error_message[:1000], "updated_at": now,
    }).eq("id", job["document_id"]).eq("workspace_id", job["workspace_id"]).execute()
    _client().table("conversation_attachments").update({"parse_status": "failed"}).eq(
        "id", job["attachment_id"]
    ).eq("workspace_id", job["workspace_id"]).execute()


def retry_document_job(document_id: str, workspace_id: str) -> dict | None:
    now = datetime.now(timezone.utc).isoformat()
    result = (
        _client().table("document_processing_jobs").update({
            "status": "queued", "attempts": 0, "error_code": None, "error_message": None,
            "queued_at": now, "started_at": None, "finished_at": None, "locked_at": None,
            "updated_at": now,
        }).eq("document_id", document_id).eq("workspace_id", workspace_id)
        .in_("status", ["partial", "completed", "failed", "needs_ocr", "ocr_unavailable"])
        .select("*").execute()
    )
    rows = _rows(result)
    if not rows:
        return None
    _client().table("documents").update({"processing_status": "queued", "last_error_code": None,
        "last_error_message": None, "updated_at": now}).eq("id", document_id).eq("workspace_id", workspace_id).execute()
    return rows[0]


def get_document_access(document_id: str, workspace_id: str) -> dict | None:
    result = (
        _client().table("documents").select("*").eq("id", document_id)
        .eq("workspace_id", workspace_id).limit(1).execute()
    )
    rows = _rows(result)
    return rows[0] if rows else None


def get_document_job(document_id: str, workspace_id: str) -> dict | None:
    result = (
        _client().table("document_processing_jobs").select("*").eq("document_id", document_id)
        .eq("workspace_id", workspace_id).eq("job_type", "extract").limit(1).execute()
    )
    rows = _rows(result)
    return rows[0] if rows else None


def list_document_rows(table: str, document_id: str, workspace_id: str, *, limit: int, offset: int) -> tuple[list[dict], int]:
    allowed = {"document_pages", "document_segments", "document_facts"}
    if table not in allowed:
        raise ValueError("Unsupported document table.")
    query = (
        _client().table(table).select("*", count="exact").eq("document_id", document_id)
        .eq("workspace_id", workspace_id)
    )
    if table == "document_pages":
        query = query.order("page_number", desc=False).order("block_index", desc=False)
    elif table == "document_segments":
        query = query.order("segment_index", desc=False)
    else:
        query = query.order("created_at", desc=False)
    result = query.range(offset, offset + limit - 1).execute()
    return _rows(result), int(result.count or 0)


def get_document_analysis(document_id: str, workspace_id: str) -> dict | None:
    document = get_document_access(document_id, workspace_id)
    if not document:
        return None
    facts, fact_count = list_document_rows("document_facts", document_id, workspace_id, limit=100, offset=0)
    metadata = document.get("processing_metadata") or {}
    return {
        "document_id": document_id, "filename": document.get("file_name", "Document"),
        "status": document.get("processing_status", "queued"),
        "document_type": document.get("document_type"),
        "classification_confidence": document.get("classification_confidence"),
        "classification": document.get("classification_provenance") or {},
        "summary": document.get("summary"),
        "summary_provenance": document.get("summary_provenance") or {},
        "page_count": document.get("page_count", 0),
        "block_count": document.get("block_count", 0),
        "extracted_characters": document.get("extracted_characters", 0),
        "facts": facts, "fact_count": fact_count,
        "uncertainty_notes": metadata.get("uncertainty_notes", []),
        "prompt_injection_detected": bool(document.get("prompt_injection_detected")),
        "prompt_injection": metadata.get("prompt_injection", {"detected": bool(document.get("prompt_injection_detected"))}),
        "omitted_context": metadata.get("omitted_context", {}),
        "last_error_code": document.get("last_error_code"),
        "last_error_message": document.get("last_error_message"),
    }
