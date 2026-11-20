from pathlib import Path
from uuid import uuid4
import re

from fastapi import APIRouter, File, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.graph.workflow import analyze_pages
from app.services.document_pipeline import process_document_bytes
from app.services.pdf_generator import generate_report
from app.services.upload_validation import validate_attachment_upload
from app.services.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/v1", tags=["documents"])
ALLOWED = {".pdf", ".docx"}


class MemorandumRequest(BaseModel):
    document_name: str = Field(default="Uploaded document", max_length=240)
    risks: list[dict] = Field(default_factory=list, max_length=100)


@router.post("/documents/analyze")
async def upload_and_analyze(request: Request, file: UploadFile = File(...)):
    """Legacy M0 endpoint; uses the M2 parser synchronously for compatibility."""
    original_name = Path(file.filename or "uploaded-document").name
    if Path(original_name).suffix.lower() not in ALLOWED:
        raise HTTPException(400, "Only PDF and DOCX files are supported on this endpoint.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    chunks: list[bytes] = []
    total_bytes = 0
    try:
        while chunk := await file.read(1024 * 1024):
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                raise HTTPException(413, f"Maximum upload size is {settings.max_upload_mb} MB.")
            chunks.append(chunk)
        content = b"".join(chunks)
        filename, _mime, _kind = validate_attachment_upload(
            original_name, content, max_bytes, max_image_pixels=settings.max_image_pixels,
            max_image_bytes=settings.max_image_upload_mb * 1024 * 1024,
        )
        if Path(filename).suffix.lower() not in ALLOWED:
            raise HTTPException(400, "Only PDF and DOCX files are supported on this endpoint.")
        result = process_document_bytes(filename, content)
        pages = [
            {"page": page.get("page_number"), "text": page.get("text", ""), "locator": page.get("source_locator")}
            for page in result.get("pages", [])
        ]
        classification = result["classification"]
        analysis_method = "document_classifier"
        analysis_notice = "এই নথি M2 evidence-preserving extraction দিয়ে বিশ্লেষণ করা হয়েছে।"
        risks = []
        if classification.get("document_type") == "contract" and result.get("status") in {"completed", "partial"}:
            risks, analysis_method, analysis_notice = await analyze_pages(pages)
        extracted_text = "\n".join(str(block.get("text", "")) for block in result.get("blocks", []))
        document_id = str(uuid4())
        upload_dir = settings.upload_path
        upload_dir.mkdir(parents=True, exist_ok=True)
        stored = upload_dir / f"{document_id}{Path(filename).suffix.lower()}"
        stored.write_bytes(content)
        try:
            get_supabase_client().table("legacy_document_owners").insert({
                "document_id": document_id,
                "user_id": str(request.state.user["id"]),
            }).execute()
        except Exception as exc:
            stored.unlink(missing_ok=True)
            raise HTTPException(503, "Document ownership record could not be saved. Apply migration 004 and check Supabase.") from exc
        return {
            "document_id": document_id,
            "filename": filename,
            **classification,
            "status": result.get("status", "failed"),
            "analysis_method": analysis_method,
            "analysis_notice": analysis_notice,
            "summary": result.get("summary"),
            "summary_provenance": result.get("summary_provenance"),
            "facts": result.get("facts", []),
            "uncertainty_notes": result.get("uncertainty_notes", []),
            "prompt_injection": result.get("prompt_injection", {}),
            "extracted_characters": len(extracted_text),
            "page_count": result.get("page_count", 0),
            "block_count": result.get("block_count", 0),
            "risks": [risk.model_dump() if hasattr(risk, "model_dump") else risk for risk in risks],
            "legal_citations": [],
            "citation_notice": (
                "No legal citations have been verified. Statutory retrieval, amendment/status "
                "checks and applicability analysis are not yet implemented."
            ),
            "pipeline": {
                "document_extraction": result.get("status"),
                "ocr": "completed" if any(page.get("ocr_text") for page in result.get("pages", [])) else "not_needed_or_unavailable",
                "document_evidence_validation": "exact_quote_checked",
                "document_chat": "available_in_conversation_upload_flow",
                "bangladesh_legal_research": "not_implemented",
                "citation_verification": "not_implemented",
                "memorandum_generation": "available_on_request",
            },
            "disclaimer": (
                "Preliminary AI-assisted document screening only; not legal advice. "
                "Document quote matching does not verify legal authority, current law, "
                "amendments, commencement or applicability."
            ),
        }
    finally:
        await file.close()


@router.post("/memoranda/{document_id}/pdf")
async def create_pdf(document_id: str, payload: MemorandumRequest):
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", document_id)
    if not safe_id:
        raise HTTPException(400, "Invalid document id.")
    filename = f"{safe_id}-memorandum.pdf"
    path = generate_report(
        filename=filename,
        document_name=payload.document_name,
        risks=payload.risks,
        report_dir=str(settings.report_path),
    )
    return FileResponse(path, media_type="application/pdf", filename=filename)
