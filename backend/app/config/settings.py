from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    upload_dir: str = "uploads"
    report_dir: str = "reports"
    max_upload_mb: int = 20
    openrouter_api_key: str = Field(default="", repr=False)
    openrouter_model: str = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "http://localhost:3000"
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = Field(default="", repr=False)
    super_admin_email: str = ""
    super_admin_password: str = Field(default="", repr=False)
    max_conversation_attachments: int = 8
    max_chat_context_chars: int = 90000
    max_image_pixels: int = 40_000_000
    max_image_upload_mb: int = 8
    max_pdf_pages: int = 500
    ocr_languages: str = "ben+eng"
    tesseract_cmd: str = "tesseract"
    ocr_dpi: int = 200
    ocr_min_text_chars: int = 30
    document_segment_chars: int = 6000
    document_segment_overlap_chars: int = 300
    document_worker_poll_seconds: int = 5
    max_document_response_text_chars: int = 12000

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @staticmethod
    def _backend_path(value: str) -> Path:
        """Resolve storage paths relative to backend/, never the shell CWD."""
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return path.resolve()

    @property
    def upload_path(self) -> Path:
        return self._backend_path(self.upload_dir)

    @property
    def report_path(self) -> Path:
        return self._backend_path(self.report_dir)


settings = Settings()
