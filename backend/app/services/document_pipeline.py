from __future__ import annotations

import io
import re
import tempfile
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

from app.config.settings import settings
from app.services.document_facts import extract_candidate_facts
from app.services.document_intelligence import classify_document
from app.services.document_parser import DocumentParseError, extract_document
from app.services.document_segmentation import segment_blocks
from app.services.ocr import OCRProvider, OCRUnavailableError, TesseractOCRProvider

INJECTION_PATTERNS = {
    "ignore_prior_instructions": re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    "system_prompt_override": re.compile(r"(reveal|print|show|ignore).{0,40}(system prompt|developer message|hidden instructions)", re.I),
    "role_impersonation": re.compile(r"(?:^|\n)\s*(?:system|developer|assistant)\s*:\s", re.I),
    "tool_or_secret_exfiltration": re.compile(r"(api key|password|secret|credential).{0,40}(send|upload|reveal|exfiltrat)", re.I),
}


def detect_prompt_injection(text: str) -> dict[str, Any]:
    matches = [name for name, pattern in INJECTION_PATTERNS.items() if pattern.search(text or "")]
    return {"detected": bool(matches), "signals": matches, "handling": "content_remains_untrusted_and_is_not_executed"}


def _render_pdf_page(path: str, page_number: int, dpi: int, max_pixels: int) -> bytes:
    with fitz.open(path) as document:
        page = document[page_number - 1]
        scale = dpi / 72
        rect = page.rect
        estimated = rect.width * scale * rect.height * scale
        if estimated > max_pixels:
            # Downscale before rendering so oversized pages never allocate a huge pixmap.
            scale *= (max_pixels / estimated) ** 0.5
        estimated_width = max(1, int(rect.width * scale))
        estimated_height = max(1, int(rect.height * scale))
        if estimated_width * estimated_height > max_pixels:
            raise RuntimeError("PDF page cannot be rendered within the configured pixel safety limit.")
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        if pixmap.width * pixmap.height > max_pixels:
            raise RuntimeError("Rendered PDF page exceeded the configured image pixel limit.")
        return pixmap.tobytes("png")


def _summary(blocks: list[dict[str, Any]], classification: dict[str, Any]) -> str:
    excerpts = []
    for block in blocks:
        text = re.sub(r"\s+", " ", str(block.get("text", ""))).strip()
        if len(text) >= 35:
            excerpts.append(text[:420])
        if len(excerpts) == 3:
            break
    if not excerpts:
        return "No readable source text was extracted. OCR or manual review may be required."
    label = classification.get("document_type_bn", "নথি")
    return f"Detected type: {label}. Extractive preview: " + " | ".join(excerpts)


def process_document_bytes(
    filename: str,
    content: bytes,
    *,
    ocr_provider: OCRProvider | None = None,
    ocr_languages: str | None = None,
    ocr_dpi: int | None = None,
    max_image_pixels: int | None = None,
    max_pdf_pages: int | None = None,
    segment_chars: int | None = None,
    segment_overlap_chars: int | None = None,
) -> dict[str, Any]:
    """Normalize a supported document and return evidence-bearing extraction results.

    `artifacts` contains private derived page-image bytes for the worker to store.
    """
    suffix = Path(filename).suffix.lower()
    ocr_provider = ocr_provider or TesseractOCRProvider(settings.tesseract_cmd)
    languages = ocr_languages or settings.ocr_languages
    dpi = ocr_dpi or settings.ocr_dpi
    pixel_limit = max_image_pixels or settings.max_image_pixels
    page_limit = max_pdf_pages or settings.max_pdf_pages
    artifacts: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    uncertainties: list[str] = []
    ocr_needed = False
    ocr_completed = False
    ocr_blocked = False
    ocr_failed = False
    metadata: dict[str, Any] = {"source_format": suffix.lstrip("."), "page_numbers_available": suffix == ".pdf"}

    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            with Image.open(io.BytesIO(content)) as image:
                width, height = image.size
                image_format = image.format
                if width * height > pixel_limit:
                    raise ValueError("Image dimensions exceed configured pixel safety limit.")
                image.verify()
        except Exception as exc:
            raise DocumentParseError(f"Image is malformed or exceeds the pixel limit: {type(exc).__name__}.") from exc
        metadata.update({"width": width, "height": height, "image_format": image_format, "image_vision_status": "not_requested"})
        ocr_needed = True
        locator = {"kind": "image", "page_number": 1, "block_index": 1, "start_offset": 0}
        try:
            result = ocr_provider.extract(content, languages)
            ocr_completed = True
            text = result.text
            page = {
                "page_number": 1, "block_index": 1, "source_text": "", "ocr_text": text,
                "text": text, "source_type": "ocr_text", "ocr_status": "completed",
                "ocr_engine": result.engine, "ocr_languages": result.languages,
                "ocr_confidence": result.confidence, "image_width": width, "image_height": height,
                "artifact_type": "normalized_image",
                "source_locator": locator,
            }
            if not text.strip():
                page["ocr_status"] = "needs_ocr"
                uncertainties.append("OCR completed but returned no readable text for the image.")
            pages.append(page)
            if text.strip():
                blocks.append({"text": text, "source_type": "ocr_text", "locator": locator})
        except OCRUnavailableError as exc:
            ocr_blocked = True
            uncertainties.append(str(exc))
            pages.append({
                "page_number": 1, "block_index": 1, "source_text": "", "ocr_text": "", "text": "",
                "source_type": "ocr_text", "ocr_status": "ocr_unavailable",
                "ocr_engine": "tesseract", "ocr_languages": languages.split("+"),
                "image_width": width, "image_height": height, "artifact_type": "normalized_image",
                "source_locator": locator,
            })
        except Exception as exc:
            ocr_failed = True
            uncertainties.append(f"Image OCR failed: {type(exc).__name__}.")
            pages.append({
                "page_number": 1, "block_index": 1, "source_text": "", "ocr_text": "", "text": "",
                "source_type": "ocr_text", "ocr_status": "failed", "ocr_engine": "tesseract",
                "ocr_languages": languages.split("+"), "image_width": width, "image_height": height,
                "artifact_type": "normalized_image", "source_locator": locator,
            })
        artifacts.append({"artifact_type": "normalized_image", "page_number": 1, "mime_type": "image/png", "content": _normalize_image(content, pixel_limit)})

    elif suffix in {".pdf", ".docx"}:
        with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            parsed = extract_document(temp_file.name, max_pdf_pages=page_limit)
            metadata.update(parsed.metadata)
            if suffix == ".pdf":
                for page in parsed.pages:
                    page_number = int(page["page"])
                    source_text = str(page.get("text") or "")
                    ocr_text = ""
                    ocr_status = "not_needed"
                    image_artifact = None
                    if len(source_text.strip()) < settings.ocr_min_text_chars:
                        ocr_needed = True
                        try:
                            image_artifact = _render_pdf_page(temp_file.name, page_number, dpi, pixel_limit)
                            artifacts.append({"artifact_type": "page_image", "page_number": page_number, "mime_type": "image/png", "content": image_artifact})
                            result = ocr_provider.extract(image_artifact, languages)
                            ocr_completed = True
                            ocr_text = result.text
                            ocr_status = "completed" if ocr_text.strip() else "needs_ocr"
                            if not ocr_text.strip():
                                uncertainties.append(f"OCR returned no readable text for page {page_number}.")
                        except OCRUnavailableError as exc:
                            ocr_blocked = True
                            ocr_status = "ocr_unavailable"
                            uncertainties.append(f"Page {page_number}: {exc}")
                        except Exception as exc:
                            ocr_failed = True
                            ocr_status = "failed"
                            uncertainties.append(f"OCR failed for page {page_number}: {type(exc).__name__}.")
                    combined = "\n".join(part for part in (source_text, ocr_text) if part).strip()
                    page_record = {
                        "page_number": page_number, "block_index": page_number,
                        "source_text": source_text, "ocr_text": ocr_text, "text": combined,
                        "source_type": "mixed" if source_text and ocr_text else "ocr_text" if ocr_text else "source_text",
                        "source_locator": {"kind": "pdf_page", "page_number": page_number, "block_index": page_number},
                        "ocr_status": ocr_status,
                        "ocr_engine": "tesseract" if ocr_status in {"completed", "failed", "ocr_unavailable", "needs_ocr"} else None,
                    }
                    pages.append(page_record)
                    if source_text.strip():
                        blocks.append({"text": source_text, "source_type": "source_text", "locator": {"kind": "pdf_page", "page_number": page_number, "block_index": page_number, "start_offset": 0}})
                    if ocr_text.strip():
                        blocks.append({"text": ocr_text, "source_type": "ocr_text", "locator": {"kind": "pdf_page_ocr", "page_number": page_number, "block_index": page_number, "start_offset": 0}})
            else:
                blocks = parsed.blocks
                pages = []
                # Each DOCX paragraph/table cell is a source block, never a fabricated PDF page.
                for block in blocks:
                    locator = dict(block["locator"])
                    block["locator"] = {**locator, "start_offset": 0, "end_offset": len(block["text"])}
                    pages.append({
                        "page_number": None,
                        "block_index": locator.get("block_index"),
                        "source_text": block["text"], "ocr_text": "", "text": block["text"],
                        "source_type": "source_text", "ocr_status": "not_needed",
                        "source_locator": block["locator"],
                    })
                metadata["page_count"] = 0
    else:
        raise DocumentParseError("Supported formats are PDF, DOCX, PNG, JPG/JPEG and WEBP.")

    source_pages = []
    for page in pages:
        if page.get("text"):
            source_pages.append({
                "page": page.get("page_number"), "text": page["text"],
                "locator": {"kind": "page", "page_number": page.get("page_number"), "block_index": page.get("block_index")},
            })
    if not source_pages and blocks:
        source_pages = [{"page": None, "text": item["text"], "locator": item["locator"]} for item in blocks]
    classification = classify_document(source_pages)
    facts = extract_candidate_facts(blocks)
    segments = segment_blocks(
        blocks,
        max_chars=segment_chars or settings.document_segment_chars,
        overlap_chars=segment_overlap_chars if segment_overlap_chars is not None else settings.document_segment_overlap_chars,
    )
    all_text = "\n".join(str(item.get("text", "")) for item in blocks)
    injection = detect_prompt_injection(all_text)

    if ocr_needed and ocr_blocked and not any(item.get("text", "").strip() for item in blocks):
        status = "ocr_unavailable"
    elif ocr_needed and not any(item.get("text", "").strip() for item in blocks) and pages and all(item.get("ocr_status") == "needs_ocr" for item in pages):
        status = "needs_ocr"
    elif ocr_failed or (ocr_needed and ocr_blocked) or any(item.get("ocr_status") == "needs_ocr" for item in pages):
        status = "partial"
    elif ocr_needed and not ocr_completed and not any(item.get("text", "").strip() for item in blocks):
        status = "needs_ocr"
    elif not blocks:
        status = "needs_ocr" if ocr_needed else "failed"
    else:
        status = "completed"

    summary = _summary(blocks, classification)
    return {
        "status": status,
        "pages": pages,
        "blocks": blocks,
        "segments": segments,
        "facts": facts,
        "classification": classification,
        "summary": summary,
        "summary_provenance": {"type": "extractive_preview", "method": "source_text_excerpt", "model_generated": False},
        "uncertainty_notes": uncertainties,
        "prompt_injection": injection,
        "metadata": metadata,
        "page_count": sum(1 for page in pages if page.get("page_number") is not None),
        "block_count": len(blocks),
        "extracted_characters": len(all_text),
        "artifacts": artifacts,
    }


def _normalize_image(content: bytes, max_pixels: int) -> bytes:
    with Image.open(io.BytesIO(content)) as image:
        image.load()
        if image.width * image.height > max_pixels:
            raise ValueError("Image exceeds pixel limit.")
        converted = image.convert("RGB")
        output = io.BytesIO()
        converted.save(output, format="PNG", optimize=True)
        return output.getvalue()
