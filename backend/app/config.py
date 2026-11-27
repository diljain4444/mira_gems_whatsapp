"""
config.py — Application settings loaded from .env
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    mira_gems_api_key: str = ""
    database_url: str = ""
    backend_allowed_origins: str = "http://localhost:5173,chrome-extension://*"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
