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
    gemini_api_key: str = Field(default="", repr=False)
    gemini_model: str = "gemini-3.8-flash"
    supabase_url: str = ""
    supabase_service_role_key: str = Field(default="", repr=False)

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
