import os
import unittest
from pathlib import Path

from app.config.settings import BACKEND_DIR, Settings


class StoragePathTests(unittest.TestCase):
    def test_relative_storage_paths_resolve_against_backend_directory(self):
        config = Settings(_env_file=None, upload_dir="uploads", report_dir="reports")
        self.assertEqual(config.upload_path, (BACKEND_DIR / "uploads").resolve())
        self.assertEqual(config.report_path, (BACKEND_DIR / "reports").resolve())

    def test_absolute_storage_path_is_preserved(self):
        absolute = (BACKEND_DIR.parent / "legal-copilot-test-uploads").resolve()
        config = Settings(_env_file=None, upload_dir=str(absolute))
        self.assertEqual(config.upload_path, absolute)


if __name__ == "__main__":
    unittest.main()
