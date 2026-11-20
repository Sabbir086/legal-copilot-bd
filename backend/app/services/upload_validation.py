from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException


DOCUMENT_SUFFIXES = {".pdf", ".docx"}
IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def validate_attachment_upload(filename: str, content: bytes, max_bytes: int) -> tuple[str, str, str]:
    """Validate supported document/image formats and basic file signatures.

    This is a format check, not malware scanning or document sanitization.
    Returns (safe filename, MIME type, attachment kind).
    """
    safe_name = Path(filename or "uploaded-file").name
    suffix = Path(safe_name).suffix.lower()
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(content) > max_bytes:
        raise HTTPException(413, f"Maximum upload size is {max_bytes // (1024 * 1024)} MB per file.")

    if suffix == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(400, "The uploaded file does not appear to be a valid PDF.")
        return safe_name, "application/pdf", "document"

    if suffix == ".docx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                names = set(archive.namelist())
                if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                    raise HTTPException(400, "The uploaded file does not appear to be a valid DOCX.")
        except BadZipFile as exc:
            raise HTTPException(400, "The uploaded file does not appear to be a valid DOCX.") from exc
        return safe_name, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "document"

    if suffix in IMAGE_MIME_TYPES:
        if suffix == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(400, "The uploaded file does not appear to be a valid PNG image.")
        if suffix in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
            raise HTTPException(400, "The uploaded file does not appear to be a valid JPEG image.")
        if suffix == ".webp" and not (content.startswith(b"RIFF") and content[8:12] == b"WEBP"):
            raise HTTPException(400, "The uploaded file does not appear to be a valid WEBP image.")
        if len(content) > 8 * 1024 * 1024:
            raise HTTPException(413, "Image upload size is limited to 8 MB per image in M1.")
        return safe_name, IMAGE_MIME_TYPES[suffix], "image"

    raise HTTPException(400, "Supported attachments: PDF, DOCX, PNG, JPG/JPEG and WEBP.")


def validate_document_upload(filename: str, content: bytes, max_bytes: int) -> tuple[str, str]:
    """Backward-compatible validator for the M0 single-document endpoint."""
    safe_name, mime_type, kind = validate_attachment_upload(filename, content, max_bytes)
    if kind != "document":
        raise HTTPException(400, "Only PDF and DOCX files are supported on this endpoint.")
    return safe_name, mime_type
