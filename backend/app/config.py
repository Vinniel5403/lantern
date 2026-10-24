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
    # Safe default; local integration can temporarily disable the gate via env.
    require_wake_word: bool = True
    wake_phrase: str = "\u0e41\u0e25\u0e19\u0e40\u0e17\u0e34\u0e23\u0e4c\u0e19"
    wake_word_alternatives: str = "lantern,\u0e41\u0e25\u0e19\u0e40\u0e17\u0e34\u0e19,\u0e41\u0e25\u0e19\u0e40\u0e17\u0e34\u0e48\u0e19,\u0e41\u0e25\u0e19\u0e40\u0e17\u0e34\u0e23\u0e19"
    duplicate_window_s: float = Field(default=30.0, ge=0)
    duplicate_cache_size: int = Field(default=128, gt=0)
    request_replay_window_s: float = Field(default=60.0, ge=0)
    request_replay_cache_size: int = Field(default=128, gt=0)
    typhoon_api_key: str | None = None
    typhoon_api_base_url: str = "https://api.opentyphoon.ai/v1"
    typhoon_asr_model: str = "typhoon-asr-realtime"
    typhoon_api_timeout_s: float = Field(default=30.0, gt=0)
    typhoon_self_host_url: str = "http://127.0.0.1:8001"


@lru_cache
def get_settings() -> Settings:
    return Settings()
