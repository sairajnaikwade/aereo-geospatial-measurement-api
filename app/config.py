from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Application Settings configured via environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    APP_NAME: str = "Geospatial File Measurement API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api"

    # PostgreSQL Database URL (uses psycopg2 driver)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/geomeasurement_db"

    # Security & Upload Limits
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    ALLOWED_EXTENSIONS: str = ".kml,.zip"

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()]

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("Only PostgreSQL is supported as the database backend.")
        # Normalize bare postgresql:// to postgresql+psycopg2:// for explicit driver compatibility
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v


settings = Settings()
