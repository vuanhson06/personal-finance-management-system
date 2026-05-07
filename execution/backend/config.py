import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_env_path)


def _require_env(key: str) -> str:
    value: str | None = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"[CONFIG ERROR] Required environment variable '{key}' is not set. "
            f"Please check your .env file against .env.example."
        )
    return value


@dataclass
class Settings:
    db_host: str = field(default_factory=lambda: _require_env("DB_HOST"))
    db_port: str = field(default_factory=lambda: os.getenv("DB_PORT", "3306"))
    db_user: str = field(default_factory=lambda: _require_env("DB_USER"))
    db_password: str = field(default_factory=lambda: _require_env("DB_PASSWORD"))
    db_name: str = field(default_factory=lambda: _require_env("DB_NAME"))

    webhook_api_key: str = field(default_factory=lambda: _require_env("WEBHOOK_API_KEY"))

    @property
    def database_url(self) -> str:
        return (
            f"mysql+mysqlconnector://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings: Settings = Settings()
