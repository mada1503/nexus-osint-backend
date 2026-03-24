"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    SECRET_KEY: str = "change-me"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "*"

    DATABASE_URL: str = "postgresql+asyncpg://nexus_user:nexus_password@localhost:5432/nexus_db"

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # API Keys
    GOOGLE_API_KEY: str = ""
    GOOGLE_CSE_ID: str = ""
    HUNTER_API_KEY: str = ""
    SHODAN_API_KEY: str = ""
    HIBP_API_KEY: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
