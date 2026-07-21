"""Application configuration using Pydantic settings."""

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required — app cannot start without these
    supabase_url: str
    supabase_key: str

    # Aquifer API
    aquifer_api_key: str | None = None
    aquifer_base_url: str = "https://api.aquifer.bible"

    # Application
    environment: str = "development"
    log_level: str = "INFO"

    # CORS — comma-separated in env (CORS_ORIGINS)
    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        validation_alias="CORS_ORIGINS",
    )

    # Server
    server_host: str = "127.0.0.1"
    server_port: int = 8000

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


settings = Settings()
