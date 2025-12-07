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
    
    # Grok API Rate Limiting
    grok_max_requests_per_minute: int = 60  # Conservative default
    grok_max_concurrent_requests: int = 10  # Limit parallel requests
    grok_rate_limit_retry_attempts: int = 5  # Max retries for rate limits

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
