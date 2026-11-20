from __future__ import annotations

import warnings
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError


DOCUMENT_SUFFIXES = {".pdf", ".docx"}
IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_DOCX_ENTRIES = 5000
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_DOCX_COMPRESSION_RATIO = 250
DEFAULT_MAX_IMAGE_PIXELS = 40_000_000


def _validate_docx(content: bytes) -> None:
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_DOCX_ENTRIES:
                raise HTTPException(413, "DOCX contains too many internal files to process safely.")
            total_uncompressed = sum(entry.file_size for entry in entries)
            if total_uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise HTTPException(413, "DOCX expands beyond the permitted processing size.")
            for entry in entries:
                if entry.file_size and entry.compress_size == 0:
                    raise HTTPException(400, "DOCX contains an invalid compressed entry.")
                if entry.compress_size and entry.file_size / entry.compress_size > MAX_DOCX_COMPRESSION_RATIO:
                    raise HTTPException(413, "DOCX compression ratio exceeds the safe limit.")
                normalized_name = entry.filename.replace("\\", "/")
                if normalized_name.startswith("/") or ".." in PurePosixPath(normalized_name).parts:
                    raise HTTPException(400, "DOCX contains an unsafe internal path.")
            names = {entry.filename for entry in entries}
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                raise HTTPException(400, "The uploaded file does not appear to be a valid DOCX document.")
            content_types_bytes = archive.read("[Content_Types].xml")
            content_types = ET.fromstring(content_types_bytes)
            document_xml = ET.fromstring(archive.read("word/document.xml"))
            if not list(document_xml) or "wordprocessingml.document.main+xml" not in content_types_bytes.decode("utf-8", errors="ignore"):
                raise HTTPException(400, "The uploaded file is not a valid WordprocessingML DOCX document.")
    except (BadZipFile, ET.ParseError, KeyError) as exc:
        raise HTTPException(400, "The uploaded file does not appear to be a valid DOCX document.") from exc


def _validate_image(content: bytes, suffix: str, max_image_pixels: int) -> tuple[int, int]:
    signature_format = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".webp": "WEBP",
    }[suffix]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.format != signature_format:
                    raise HTTPException(400, "The file signature does not match its filename extension.")
                width, height = image.size
                if width <= 0 or height <= 0 or width * height > max_image_pixels:
                    raise HTTPException(413, f"Image dimensions exceed the {max_image_pixels:,}-pixel safety limit.")
                image.verify()
                return width, height
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(413, "Image exceeds the safe pixel/decompression limit.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise HTTPException(400, "The uploaded image is malformed or unreadable.") from exc


def validate_attachment_upload(
    filename: str,
    content: bytes,
    max_bytes: int,
    *,
    max_image_pixels: int = DEFAULT_MAX_IMAGE_PIXELS,
    max_image_bytes: int = 8 * 1024 * 1024,
) -> tuple[str, str, str]:
    """Verify actual file content and return (safe filename, MIME type, kind).

    Browser-provided content types are deliberately not accepted as evidence.
    This check is not malware scanning or content disarm/reconstruction.
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
        _validate_docx(content)
        return safe_name, DOCX_MIME, "document"

    if suffix in IMAGE_MIME_TYPES:
        if len(content) > max_image_bytes:
            limit_mb = max(1, max_image_bytes // (1024 * 1024))
            raise HTTPException(413, f"Image upload size is limited to {limit_mb} MB per image.")
        _validate_image(content, suffix, max_image_pixels)
        return safe_name, IMAGE_MIME_TYPES[suffix], "image"

    raise HTTPException(400, "Supported attachments: PDF, DOCX, PNG, JPG/JPEG and WEBP.")


def validate_document_upload(filename: str, content: bytes, max_bytes: int) -> tuple[str, str]:
    """Backward-compatible validator for the M0 single-document endpoint."""
    safe_name, mime_type, kind = validate_attachment_upload(filename, content, max_bytes)
    if kind != "document":
        raise HTTPException(400, "Only PDF and DOCX files are supported on this endpoint.")
    return safe_name, mime_type
