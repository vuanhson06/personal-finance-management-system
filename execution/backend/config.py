"""
config.py — Application Configuration Module
=============================================
Loads all sensitive credentials and application settings from the `.env` file
using `python-dotenv`. Exposes a single `settings` instance (Settings dataclass)
that is the single source of truth for all configuration values across the backend.

Directive Reference: directives/backend_logic_rules.md — Section 4 (Environment Parity)
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load the .env file from the project root (two levels up from this file)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_env_path)


def _require_env(key: str) -> str:
    """
    Retrieves a required environment variable by key.
    Raises a clear EnvironmentError if the variable is not set,
    preventing silent misconfigurations.

    Args:
        key: The name of the environment variable.

    Returns:
        The string value of the environment variable.

    Raises:
        EnvironmentError: If the variable is not found in the environment.
    """
    value: str | None = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"[CONFIG ERROR] Required environment variable '{key}' is not set. "
            f"Please check your .env file against .env.example."
        )
    return value


@dataclass
class Settings:
    """
    Typed configuration container for the Personal Finance Management System.
    All values are sourced exclusively from environment variables to ensure
    no secrets are ever hardcoded in source code.
    """

    # --- Database Credentials ---
    db_host: str = field(default_factory=lambda: _require_env("DB_HOST"))
    db_port: str = field(default_factory=lambda: os.getenv("DB_PORT", "3306"))
    db_user: str = field(default_factory=lambda: _require_env("DB_USER"))
    db_password: str = field(default_factory=lambda: _require_env("DB_PASSWORD"))
    db_name: str = field(default_factory=lambda: _require_env("DB_NAME"))

    # --- Webhook Security ---
    webhook_api_key: str = field(default_factory=lambda: _require_env("WEBHOOK_API_KEY"))

    @property
    def database_url(self) -> str:
        """
        Constructs the full SQLAlchemy-compatible MySQL connection URL.
        Format: mysql+mysqlconnector://user:password@host:port/dbname

        Returns:
            A fully formed database connection string.
        """
        return (
            f"mysql+mysqlconnector://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


# Module-level singleton — import this instance across the entire backend.
settings: Settings = Settings()
