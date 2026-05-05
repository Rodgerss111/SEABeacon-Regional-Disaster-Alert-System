from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PACKAGE_ROOT = Path(__file__).resolve().parent
FIXTURES_DIR = PACKAGE_ROOT / "fixtures"
REPO_ROOT = PACKAGE_ROOT.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", str(REPO_ROOT / ".env")],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    database_url: str = Field(default="sqlite:///./seabeacon.db", alias="DATABASE_URL")
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
