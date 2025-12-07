"""
Database utility functions
"""
from typing import Any, Dict
from datetime import datetime
import uuid


def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())


def now_iso() -> str:
    """Get current UTC time as ISO format string"""
    return datetime.utcnow().isoformat()


def prepare_data(data: Dict[str, Any], add_timestamps: bool = True) -> Dict[str, Any]:
    """
    Prepare data dict for database insertion
    
    Args:
        data: Data dictionary
        add_timestamps: If True, add created_at timestamp
    
    Returns:
        Prepared data dictionary
    """
    prepared = data.copy()
    
    if "id" not in prepared:
        prepared["id"] = generate_uuid()
    
    if add_timestamps and "created_at" not in prepared:
        prepared["created_at"] = now_iso()
    
    return prepared


def format_uuid(uuid_value: Any) -> str:
    """
    Format UUID to string (handles UUID objects and strings)
    
    Args:
        uuid_value: UUID object or string
    
    Returns:
        UUID string
    """
    if isinstance(uuid_value, str):
        return uuid_value
    return str(uuid_value)


def parse_jsonb(value: Any) -> Dict[str, Any]:
    """
    Parse JSONB value to dict
    
    Args:
        value: JSONB value (dict, string, or None)
    
    Returns:
        Parsed dict or empty dict
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        import json
        try:
            return json.loads(value)
        except:
            return {}
    return {}


def build_filter_query(base_query, filters: Dict[str, Any]):
    """
    Apply filters to a Supabase query
    
    Args:
        base_query: Supabase query object
        filters: Dict of column: value pairs
    
    Returns:
        Query with filters applied
    """
    for column, value in filters.items():
        if value is not None:
            base_query = base_query.eq(column, value)
    return base_query

