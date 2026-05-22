"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central configuration for the API."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Corporate Signal Intelligence API"
    APP_ENV: str = "development"
    DATA_DIR: str = "data"
    MODELS_DIR: str = "models"
    MODEL_PATH: str = "models/isolation_forest_anomaly_pipeline.joblib"

    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    DATABASE_URL: str | None = None
    DATA_SOURCE: str = "auto"  # auto | csv | database
    BRIEFING_PROMPT_VERSION: str = "v2"
    SEC_USER_AGENT: str | None = None
    STOOQ_API_KEY: str | None = None
    ALPHA_VANTAGE_API_KEY: str | None = None
    PORT: int = 8000
    # Comma-separated extra origins (Render dashboard), e.g. http://192.168.1.59:3000
    CORS_ORIGINS: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        """Default dashboard origins plus CORS_ORIGINS from env."""
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://corporate-signal-intelligence.onrender.com",
        ]
        if self.CORS_ORIGINS:
            for part in self.CORS_ORIGINS.split(","):
                origin = part.strip()
                if origin:
                    origins.append(origin)
        seen: set[str] = set()
        unique: list[str] = []
        for origin in origins:
            if origin not in seen:
                seen.add(origin)
                unique.append(origin)
        return unique

    @property
    def data_path(self) -> Path:
        """Absolute path to the data directory."""
        path = Path(self.DATA_DIR)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def models_path(self) -> Path:
        """Absolute path to the models directory."""
        path = Path(self.MODELS_DIR)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def model_file_path(self) -> Path:
        """Absolute path to the trained model artifact."""
        path = Path(self.MODEL_PATH)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() in {"development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
