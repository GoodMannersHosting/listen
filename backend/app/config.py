from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: str = "dev"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Storage / DB
    database_url: str = "sqlite:////data/listen.db"
    upload_dir: str = "/data/uploads"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672//"

    # Whisper
    whisper_model: str = "base"
    # auto|cpu|cuda (use cpu if no GPU/CUDA runtime in container)
    whisper_device: str = "auto"
    audio_chunk_seconds: int = 15

    # OpenWebUI / Ollama-compatible OpenAI API
    openwebui_url: str = "https://ollama.cloud.danmanners.com/api/v1/chat/completions"
    openwebui_api_key: str | None = None
    openwebui_default_model: str = "gpt-oss:20b"
    openwebui_temperature: float = 0.7
    openwebui_max_tokens: int = 65535


settings = Settings()

