from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://job_scout:local_dev_only@localhost:5432/job_scout"
    log_level: str = "INFO"
    indeed_api_key: str = ""
    glassdoor_csrf_token: str = ""
    discord_webhook_url: str = ""
    discord_mention_user_id: str = ""
    # A model that rescues questions the keyword rules cannot read (any OpenAI-style API, e.g.
    # OpenRouter or Ollama). Off until llm_api_key is set. The default is a free OpenRouter model
    # that supports strict JSON-schema output; if it misbehaves or is retired, set LLM_MODEL.
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "baidu/ernie-5.5-flash-preview:free"
    llm_timeout: float = 20
    llm_min_interval: float = 60  # seconds between model calls, for the whole app
    chat_vocab_ttl: float = 600  # seconds the known job-title words are cached


settings = Settings()
