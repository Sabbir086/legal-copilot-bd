import unittest
from io import BytesIO
from zipfile import ZipFile

from fastapi import HTTPException

from app.services.upload_validation import validate_attachment_upload, validate_document_upload


class AttachmentValidationTests(unittest.TestCase):
    def test_pdf_signature_is_required(self):
        name, mime, kind = validate_attachment_upload("notice.pdf", b"%PDF-1.7 sample", 1024)
        self.assertEqual((name, mime, kind), ("notice.pdf", "application/pdf", "document"))
        with self.assertRaises(HTTPException):
            validate_attachment_upload("notice.pdf", b"not a pdf", 1024)

    def test_docx_zip_structure_is_required(self):
        buffer = BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        name, mime, kind = validate_attachment_upload("contract.docx", buffer.getvalue(), 4096)
        self.assertEqual(name, "contract.docx")
        self.assertEqual(kind, "document")
        self.assertIn("officedocument.wordprocessingml.document", mime)

    def test_png_image_is_supported(self):
        png = b"\x89PNG\r\n\x1a\n" + (b"0" * 16)
        name, mime, kind = validate_attachment_upload("scan.png", png, 4096)
        self.assertEqual((name, mime, kind), ("scan.png", "image/png", "image"))

    def test_jpeg_image_is_supported(self):
        jpeg = b"\xff\xd8\xff" + (b"0" * 16)
        _, mime, kind = validate_attachment_upload("photo.jpg", jpeg, 4096)
        self.assertEqual((mime, kind), ("image/jpeg", "image"))

    def test_webp_signature_is_required(self):
        webp = b"RIFF" + (b"0" * 4) + b"WEBP" + (b"0" * 8)
        self.assertEqual(validate_attachment_upload("scan.webp", webp, 4096)[1:], ("image/webp", "image"))
        with self.assertRaises(HTTPException):
            validate_attachment_upload("scan.webp", b"bad", 4096)

    def test_image_limit_is_eight_megabytes(self):
        png = b"\x89PNG\r\n\x1a\n" + (b"0" * (8 * 1024 * 1024))
        with self.assertRaises(HTTPException) as raised:
            validate_attachment_upload("large.png", png, 20 * 1024 * 1024)
        self.assertEqual(raised.exception.status_code, 413)

    def test_legacy_document_route_rejects_images(self):
        png = b"\x89PNG\r\n\x1a\n" + (b"0" * 16)
        with self.assertRaises(HTTPException):
            validate_document_upload("image.png", png, 1024)


if __name__ == "__main__":
    unittest.main()
