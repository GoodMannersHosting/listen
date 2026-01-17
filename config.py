"""Configuration management using Pydantic settings."""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    database_url: str = "sqlite:///./listen.db"
    
    # Transcription Model Configuration
    transcription_model: str = "whisper"
    whisper_model: str = "base"
    parakeet_model: str = "nvidia/parakeet-tdt-0.6b-v3"
    
    # Speaker Diarization Configuration
    enable_diarization: bool = False
    pyannote_pipeline: str = "community-1"
    
    # Ollama/OpenWebUI Configuration
    openwebui_url: str = "http://localhost:11434/api/chat"
    openwebui_model: str = "llama2"
    openwebui_temperature: float = 0.7
    openwebui_max_tokens: int = 2000
    openwebui_api_key: Optional[str] = None  # Add this line
    
    # Audio Processing Configuration
    audio_chunk_duration: int = 15
    upload_dir: str = "./uploads"
    
    # API Key Hashing
    api_key_hash_rounds: int = 12
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
# Global settings instance
settings = Settings()
