from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MIST Artifact"
    environment: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    upload_dir: Path = ROOT_DIR / "uploads"
    report_dir: Path = ROOT_DIR / "reports"
    cache_dir: Path = ROOT_DIR / "cache"
    plugin_dir: Path = ROOT_DIR / "plugins"

    database_url: str = "sqlite+aiosqlite:///./mist.db"
    redis_url: str = "redis://localhost:6379/0"

    ai_provider: str = "local"
    ollama_url: str = "http://localhost:11434"
    enable_external_tools: bool = False

    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
