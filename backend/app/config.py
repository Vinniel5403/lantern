from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-secret runtime settings for the Phase 0 service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    asr_provider: str = "mock"
    max_audio_bytes: int = Field(default=1_000_000, gt=0)
    save_uploaded_audio: bool = False
    audio_save_dir: str = "runtime_audio"
    wake_phrase: str = "lantern"
    typhoon_api_key: str | None = None
    typhoon_api_base_url: str = "https://api.opentyphoon.ai/v1"
    typhoon_asr_model: str = "typhoon-asr-realtime"
    typhoon_api_timeout_s: float = Field(default=30.0, gt=0)
    typhoon_self_host_url: str = "http://127.0.0.1:8001"


@lru_cache
def get_settings() -> Settings:
    return Settings()
