"""
Database client singleton
"""
from supabase import create_client, Client
from app.core.config import get_settings
from functools import lru_cache


@lru_cache()
def get_db_client() -> Client:
    """
    Get cached Supabase database client instance
    
    Returns:
        Supabase client with service role key (full database access)
    """
    settings = get_settings()
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_key
    )


# Alias for backward compatibility
get_supabase_client = get_db_client

