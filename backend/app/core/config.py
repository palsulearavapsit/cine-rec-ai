import os
from typing import Any, Dict, List, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CineRec AI"
    API_V1_STR: str = "/api/v1"

    # Supabase Credentials
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # Redis and Celery Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Temporary directory for video rendering/cutting
    SCRATCH_DIR: str = "/tmp/cinerec_scratch"

    # App Config
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Instantiate Settings. Will load from .env file or host environment
settings = Settings()

# Ensure scratch directory exists
os.makedirs(settings.SCRATCH_DIR, exist_ok=True)
