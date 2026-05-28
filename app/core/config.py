from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEDJARVIS_", env_file=".env", extra="ignore")

    app_name: str = "МедЖарвис"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str = "sqlite:///data/medjarvis.db"

    gpu_required: bool = True
    asr_model: str = "large-v3-turbo"
    asr_language: str = "ru"
    asr_compute_type: str = "int8_float16"
    asr_device: str = "cuda"

    pcm_sample_rate: int = 16000
    pcm_channels: int = 1
    vad_silence_ms: int = 850
    vad_min_speech_ms: int = 450

    llama_server_url: str = "http://127.0.0.1:8080/v1"
    llama_model: str = "qwen3-4b-q4-k-m"
    llama_timeout_s: float = 25.0
    require_llm: bool = False

    export_dir: Path = Field(default=Path("exports"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
