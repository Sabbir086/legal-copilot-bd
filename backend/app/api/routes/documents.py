from pathlib import Path
from uuid import uuid4
import re

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.graph.workflow import analyze_pages
from app.services.document_intelligence import classify_document
from app.services.document_parser import DocumentParseError, extract_text
from app.services.pdf_generator import generate_report

router = APIRouter(prefix="/api/v1", tags=["documents"])
ALLOWED = {".pdf", ".docx"}


class MemorandumRequest(BaseModel):
    document_name: str = Field(default="Uploaded document", max_length=240)
    risks: list[dict] = Field(default_factory=list, max_length=100)


@router.post("/documents/analyze")
async def upload_and_analyze(file: UploadFile = File(...)):
    original_name = Path(file.filename or "uploaded-document").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, "Only PDF and DOCX files are supported.")

    # Read in bounded chunks so an oversized body is rejected before it is
    # accumulated completely in memory.
    max_bytes = settings.max_upload_mb * 1024 * 1024
    chunks: list[bytes] = []
    total_bytes = 0
    while chunk := await file.read(1024 * 1024):
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            await file.close()
            raise HTTPException(413, f"Maximum upload size is {settings.max_upload_mb} MB.")
        chunks.append(chunk)
    content = b"".join(chunks)
    if not content:
        await file.close()
        raise HTTPException(400, "The uploaded file is empty.")

    # Basic signature checks prevent a renamed unsupported file from entering
    # the document parsers. This is not malware scanning or content sanitizing.
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        await file.close()
        raise HTTPException(400, "The uploaded file does not appear to be a valid PDF.")
    if suffix == ".docx":
        from io import BytesIO
        from zipfile import BadZipFile, ZipFile
        try:
            with ZipFile(BytesIO(content)) as archive:
                required = {"[Content_Types].xml", "word/document.xml"}
                if not required.issubset(set(archive.namelist())):
                    raise HTTPException(400, "The uploaded file does not appear to be a valid DOCX.")
        except BadZipFile as exc:
            raise HTTPException(400, "The uploaded file does not appear to be a valid DOCX.") from exc

    upload_dir = settings.upload_path
    upload_dir.mkdir(parents=True, exist_ok=True)
    document_id = str(uuid4())
    stored = upload_dir / f"{document_id}{suffix}"
    stored.write_bytes(content)

    try:
        extracted_text, pages = extract_text(str(stored))
        classification = classify_document(pages)
        if classification["document_type"] == "contract":
            risks, analysis_method, analysis_notice = await analyze_pages(pages)
        else:
            risks, analysis_method, analysis_notice = [], "document_classifier", (
                "এই নথিটি চুক্তিপত্র নয়। তাই contract-risk scan চালানো হয়নি। নথির তথ্য নিয়ে ডান পাশের সহকারীকে প্রশ্ন করতে পারেন।"
            )
    except DocumentParseError as exc:
        stored.unlink(missing_ok=True)
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        stored.unlink(missing_ok=True)
        raise HTTPException(500, "Document analysis failed. Check backend logs.") from exc
    finally:
        await file.close()

    return {
        "document_id": document_id,
        "filename": original_name,
        **classification,
        "status": "analyzed" if analysis_method == "gemini" else ("classified" if analysis_method == "document_classifier" else "screened"),
        "analysis_method": analysis_method,
        "analysis_notice": analysis_notice,
        "extracted_characters": len(extracted_text),
        "page_count": len(pages),
        "risks": [risk.model_dump() for risk in risks],
        "legal_citations": [],
        "citation_notice": (
            "No legal citations have been verified. Statutory retrieval, amendment/status "
            "checks and applicability analysis are not yet implemented."
        ),
        "pipeline": {
            "document_extraction": "completed",
            "risk_detection": (
                "completed" if analysis_method == "gemini" else
                "not_applicable_document_type" if analysis_method == "document_classifier" else
                "fallback_only"
            ),
            "document_evidence_validation": "completed" if analysis_method in {"gemini", "heuristic_fallback"} else "not_applicable",
            "document_chat": "available",
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
