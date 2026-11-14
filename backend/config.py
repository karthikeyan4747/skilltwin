"""Application settings, read only from environment variables."""

import logging
import secrets
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "prod"] = "dev"
    groq_api_key: SecretStr | None = None
    session_secret: SecretStr | None = None
    llm_model_fast: str = "openai/gpt-oss-20b"
    llm_model_smart: str = "openai/gpt-oss-120b"
    llm_model_vision: str = "qwen/qwen3.8-27b"
    adzuna_app_id: str | None = None
    adzuna_app_key: SecretStr | None = None
    database_path: Path = Path(tempfile.gettempdir()) / "skilltwin.db"
    llm_rate_limit: str = "20/minute"
    max_body_bytes: int = 2_500_000

    @model_validator(mode="after")
    def _require_secret_in_prod(self) -> "Settings":
        if self.session_secret is None:
            if self.env == "prod":
                raise ValueError("SESSION_SECRET is required when ENV=prod")
            log.warning("SESSION_SECRET not set; using a random development secret")
            self.session_secret = SecretStr(secrets.token_urlsafe(32))
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
