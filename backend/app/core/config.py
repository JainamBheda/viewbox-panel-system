from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "ViewBox Panel System"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "dev-only-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    MOCK_OTP: str = "123456"
    OTP_EXPIRY_MINUTES: int = 10
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "viewbox"
    POSTGRES_USER: str = "viewbox"
    POSTGRES_PASSWORD: str = "change-me-locally"
    DATABASE_URL: str = "postgresql+psycopg://viewbox:change-me-locally@localhost:5432/viewbox"
    TEST_DATABASE_URL: str = "sqlite:///:memory:"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    VITE_API_BASE_URL: str = "http://localhost:8000/api/v1"

    model_config = SettingsConfigDict(
        env_file=(str(ROOT / ".env"), str(ROOT / "backend" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
