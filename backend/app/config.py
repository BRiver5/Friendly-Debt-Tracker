"""Application configuration.

Values are read from environment variables so the same code runs locally
against SQLite and in production against Postgres without edits.
"""
from __future__ import annotations

import os


class Settings:
    """Runtime settings sourced from the environment."""

    # SQLite for MVP; set DATABASE_URL to a Postgres DSN in production.
    # e.g. postgresql+psycopg://user:pass@host:5432/dbname
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./friendly_debt_tracker.db",
    )

    APP_NAME: str = "Friendly Debt Tracker API"
    APP_VERSION: str = "1.0.0"

    # Comma-separated list of allowed origins for CORS. "*" during dev.
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip()
        if raw == "*" or not raw:
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
