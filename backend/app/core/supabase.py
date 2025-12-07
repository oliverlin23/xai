"""
Supabase client connection singleton
DEPRECATED: Use app.db.client.get_db_client() instead
"""
from app.db.client import get_db_client

# Backward compatibility alias
get_supabase_client = get_db_client
