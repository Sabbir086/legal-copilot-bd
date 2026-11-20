from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


class DocumentParseError(Exception):
    """Raised when a supported file is malformed or cannot be parsed."""


@dataclass
class ParsedDocument:
    source_format: str
    blocks: list[dict[str, Any]] = field(default_factory=list)
    pages: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


def _docx_blocks(path: str) -> ParsedDocument:
    document = Document(path)
    blocks: list[dict[str, Any]] = []
    paragraph_index = 0
    table_index = 0
    body = document.element.body
    for child in body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            paragraph_index += 1
            paragraph = Paragraph(child, document)
            text = paragraph.text.strip()
            if text:
                blocks.append({
                    "text": text,
                    "source_type": "source_text",
                    "locator": {
                        "kind": "docx_paragraph", "page_number": None,
                        "paragraph_index": paragraph_index,
                        "block_index": len(blocks) + 1,
                        "style": paragraph.style.name if paragraph.style else None,
                    },
                })
        elif tag == "tbl":
            table_index += 1
            table = Table(child, document)
            for row_index, row in enumerate(table.rows, start=1):
                for cell_index, cell in enumerate(row.cells, start=1):
                    for paragraph_offset, paragraph in enumerate(cell.paragraphs, start=1):
                        text = paragraph.text.strip()
                        if text:
                            blocks.append({
                                "text": text,
                                "source_type": "source_text",
                                "locator": {
                                    "kind": "docx_table_cell", "page_number": None,
                                    "table_index": table_index, "row_index": row_index,
                                    "cell_index": cell_index, "paragraph_index": paragraph_offset,
                                    "block_index": len(blocks) + 1,
                                },
                            })
    full_text = "\n".join(block["text"] for block in blocks)
    return ParsedDocument(
        source_format="docx", blocks=blocks,
        pages=[{"page": None, "text": full_text, "source_type": "source_text"}] if full_text else [],
        metadata={"paragraph_blocks": paragraph_index, "tables": table_index, "page_numbers_available": False},
        issues=[] if full_text else ["No text paragraphs or table cells were found in the DOCX."],
    )


def _pdf_blocks(path: str, max_pages: int) -> ParsedDocument:
    try:
        with fitz.open(path) as pdf:
            if pdf.is_encrypted:
                raise DocumentParseError("This PDF is password-protected. Upload an unlocked copy.")
            if len(pdf) > max_pages:
                raise DocumentParseError(f"PDF exceeds the configured {max_pages}-page processing limit.")
            pages: list[dict[str, Any]] = []
            blocks: list[dict[str, Any]] = []
            for index, page in enumerate(pdf, start=1):
                text = page.get_text("text") or ""
                image_count = len(page.get_images(full=True))
                page_data = {
                    "page": index, "text": text, "source_type": "source_text",
                    "image_count": image_count,
                    "needs_ocr": len(text.strip()) < 30 and (image_count > 0 or not text.strip()),
                }
                pages.append(page_data)
                blocks.append({
                    "text": text, "source_type": "source_text",
                    "locator": {"kind": "pdf_page", "page_number": index, "block_index": index},
                })
            return ParsedDocument(
                source_format="pdf", blocks=blocks, pages=pages,
                metadata={"page_count": len(pdf), "page_numbers_available": True},
            )
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Could not read the PDF: {type(exc).__name__}.") from exc


def extract_document(path: str, *, max_pdf_pages: int = 500) -> ParsedDocument:
    suffix = Path(path).suffix.lower()
    try:
        if suffix == ".pdf":
            return _pdf_blocks(path, max_pdf_pages)
        if suffix == ".docx":
            return _docx_blocks(path)
        raise DocumentParseError("Only PDF and DOCX files are supported by this parser.")
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Could not read the document: {type(exc).__name__}.") from exc


def extract_text(path: str, *, max_pdf_pages: int = 500) -> tuple[str, list[dict]]:
    """M0/M1-compatible interface; DOCX page=1 is a legacy display grouping only."""
    parsed = extract_document(path, max_pdf_pages=max_pdf_pages)
    combined = "\n\n".join(block["text"] for block in parsed.blocks if block["text"]).strip()
    if parsed.source_format == "docx":
        pages = [{"page": 1, "text": combined, "source_type": "source_text", "page_number_is_synthetic": True}] if combined else []
    else:
        pages = [{key: value for key, value in page.items() if key != "needs_ocr"} for page in parsed.pages]
    return combined, pages
