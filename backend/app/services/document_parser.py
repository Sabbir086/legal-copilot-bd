from pathlib import Path
import fitz
from docx import Document


class DocumentParseError(Exception):
    """Raised when a supported file cannot be parsed into selectable text."""


def extract_text(path: str) -> tuple[str, list[dict]]:
    suffix = Path(path).suffix.lower()
    pages: list[dict] = []

    try:
        if suffix == ".pdf":
            with fitz.open(path) as pdf:
                if pdf.is_encrypted:
                    raise DocumentParseError("This PDF is password-protected. Upload an unlocked copy.")
                for index, page in enumerate(pdf, start=1):
                    pages.append({"page": index, "text": page.get_text("text") or ""})
        elif suffix == ".docx":
            doc = Document(path)
            paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
            text = "\n".join(paragraphs)
            # DOCX page layout is not preserved by python-docx; the extracted text is represented as page 1.
            pages.append({"page": 1, "text": text})
        else:
            raise DocumentParseError("Only PDF and DOCX files are supported.")
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Could not read the document: {type(exc).__name__}.") from exc

    combined = "\n\n".join(item["text"] for item in pages).strip()
    if not combined:
        raise DocumentParseError(
            "No selectable text found. Scanned PDF OCR is not enabled yet; use a text-based PDF or DOCX."
        )
    return combined, pages
