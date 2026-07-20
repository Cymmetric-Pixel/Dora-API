"""Application configuration using Pydantic settings."""

import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None

    # Aquifer API
    AQUIFER_API_KEY: str | None = None
    AQUIFER_BASE_URL: str = "https://api.aquifer.bible"

    # Application Configuration
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # CORS Configuration (comma-separated in env, e.g. https://app.vercel.app)
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Server Configuration (Render injects PORT; startCommand binds 0.0.0.0)
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("SERVER_PORT", mode="before")
    @classmethod
    def port_from_render(cls, value: int | str | None) -> int:
        # Prefer Render's PORT when present
        render_port = os.environ.get("PORT")
        if render_port:
            return int(render_port)
        if value is None or value == "":
            return 8000
        return int(value)


settings = Settings()
