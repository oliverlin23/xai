"""
Application configuration using pydantic-settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
import os


def _find_env_file() -> str:
    """Find .env file in backend directory or project root"""
    # Get the directory where this config file is located
    config_dir = Path(__file__).parent.parent.parent  # backend/
    project_root = config_dir.parent  # project root
    
    # Try backend/.env first
    backend_env = config_dir / ".env"
    if backend_env.exists():
        return str(backend_env)
    
    # Try project root/.env
    root_env = project_root / ".env"
    if root_env.exists():
        return str(root_env)
    
    # Default to backend/.env (will fail if not found, but that's expected)
    return str(backend_env)


class Settings(BaseSettings):
    """Application settings"""

    # Grok API
    grok_api_key: str = ""

    # X API (for tweet lookup)
    x_bearer_token: str = ""

    # Supabase (optional - only needed for persistence)
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Agent Configuration
    agent_timeout_seconds: int = 300
    max_retries: int = 3
    
    # Grok API Rate Limiting
    grok_max_requests_per_minute: int = 60  # Conservative default
    grok_max_concurrent_requests: int = 10  # Limit parallel requests
    grok_rate_limit_retry_attempts: int = 5  # Max retries for rate limits

    class Config:
        env_file = _find_env_file()
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
