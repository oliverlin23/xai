"""
Application configuration using pydantic-settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Grok API
    grok_api_key: str

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Agent Configuration
    agent_timeout_seconds: int = 300
    max_retries: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
