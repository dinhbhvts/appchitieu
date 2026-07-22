"""Application configuration.

This module centralizes every configurable value (database URL, app name,
CORS origins) in a single place. We read them from environment variables so the
same code runs unchanged on a laptop (SQLite) and on a cloud server
(PostgreSQL). Nothing else in the codebase should read os.environ directly.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    pydantic-settings automatically loads matching keys from a local ".env"
    file and from real environment variables (env vars win over the file).
    """

    # Human-friendly name shown in the auto-generated API docs.
    app_name: str = "VibeApp - Quan ly thu chi"

    # Database connection string.
    # - Development default: a local SQLite file (no server needed).
    # - Production: set DATABASE_URL to a PostgreSQL URL, e.g.
    #   postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str = "sqlite:///./vibeapp.db"

    # Origins allowed to call this API from a browser (CORS).
    # "*" is fine while developing; tighten it in production.
    cors_origins: str = "*"

    # Tell pydantic to read a ".env" file sitting next to where we run the app.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return a single, cached Settings instance.

    lru_cache guarantees the .env file is parsed only once per process, and
    every caller shares the exact same object.
    """
    return Settings()
