from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://job_scout:local_dev_only@localhost:5432/job_scout"
    log_level: str = "INFO"
    indeed_api_key: str = ""
    glassdoor_csrf_token: str = ""


settings = Settings()
