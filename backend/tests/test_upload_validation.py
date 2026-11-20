import unittest
from io import BytesIO
from zipfile import ZipFile
from unittest.mock import patch

from fastapi import HTTPException
from PIL import Image

from app.services.upload_validation import validate_attachment_upload, validate_document_upload


def make_image(format_name: str = "PNG", size: tuple[int, int] = (8, 8)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "white").save(buffer, format=format_name)
    return buffer.getvalue()


class AttachmentValidationTests(unittest.TestCase):
    def test_pdf_signature_is_required(self):
        name, mime, kind = validate_attachment_upload("notice.pdf", b"%PDF-1.7 sample", 1024)
        self.assertEqual((name, mime, kind), ("notice.pdf", "application/pdf", "document"))
        with self.assertRaises(HTTPException):
            validate_attachment_upload("notice.pdf", b"not a pdf", 1024)

    def test_extension_signature_mismatch_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            validate_attachment_upload("renamed.pdf", make_image("PNG"), 4096)
        self.assertEqual(raised.exception.status_code, 400)

    def test_docx_zip_structure_is_required(self):
        buffer = BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", """<?xml version='1.0'?><Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'><Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/></Types>""")
            archive.writestr("word/document.xml", """<?xml version='1.0'?><w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p/></w:body></w:document>""")
        name, mime, kind = validate_attachment_upload("contract.docx", buffer.getvalue(), 4096)
        self.assertEqual(name, "contract.docx")
        self.assertEqual(kind, "document")
        self.assertIn("officedocument.wordprocessingml.document", mime)

    def test_docx_uncompressed_size_and_path_limits_are_checked_before_xml_read(self):
        large = BytesIO()
        with ZipFile(large, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
            archive.writestr("word/media/payload.bin", b"A" * 4096)
        with patch("app.services.upload_validation.MAX_DOCX_UNCOMPRESSED_BYTES", 1024):
            with self.assertRaises(HTTPException) as raised:
                validate_attachment_upload("large.docx", large.getvalue(), 20 * 1024 * 1024)
        self.assertEqual(raised.exception.status_code, 413)

        unsafe = BytesIO()
        with ZipFile(unsafe, "w") as archive:
            archive.writestr("../evil.xml", "x")
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        with self.assertRaises(HTTPException) as path_error:
            validate_attachment_upload("unsafe.docx", unsafe.getvalue(), 4096)
        self.assertEqual(path_error.exception.status_code, 400)

    def test_png_jpeg_and_webp_are_verified_by_decoder(self):
        for suffix, fmt in (("png", "PNG"), ("jpg", "JPEG"), ("webp", "WEBP")):
            _, mime, kind = validate_attachment_upload(f"scan.{suffix}", make_image(fmt), 4096)
            self.assertEqual(kind, "image")
            self.assertTrue(mime.startswith("image/"))

    def test_malformed_image_rejected(self):
        with self.assertRaises(HTTPException):
            validate_attachment_upload("scan.png", b"\x89PNG\r\n\x1a\nmalformed", 4096)

    def test_image_limit_is_eight_megabytes(self):
        payload = make_image("PNG") + b"0" * (8 * 1024 * 1024)
        with self.assertRaises(HTTPException) as raised:
            validate_attachment_upload("large.png", payload, 20 * 1024 * 1024)
        self.assertEqual(raised.exception.status_code, 413)

    def test_image_size_limit_can_be_configured(self):
        png = make_image("PNG", (2, 2))
        with self.assertRaises(HTTPException) as context:
            validate_attachment_upload(
                "tiny.png", png, len(png) + 1024,
                max_image_bytes=len(png) - 1,
            )
        self.assertEqual(context.exception.status_code, 413)

    def test_oversized_image_pixel_count_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            validate_attachment_upload("large.png", make_image(size=(100, 100)), 4096, max_image_pixels=9999)
        self.assertEqual(raised.exception.status_code, 413)

    def test_legacy_document_route_rejects_images(self):
        with self.assertRaises(HTTPException):
            validate_document_upload("image.png", make_image(), 4096)


if __name__ == "__main__":
    unittest.main()
