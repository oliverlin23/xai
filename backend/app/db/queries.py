"""
Query builder utilities for common database operations
"""
from typing import Dict, Any, List, Optional
from supabase import Client
from datetime import datetime
import uuid


class QueryBuilder:
    """Helper class for building common database queries"""
    
    def __init__(self, client: Client, table_name: str):
        """
        Initialize query builder for a specific table
        
        Args:
            client: Supabase client instance
            table_name: Name of the table to query
        """
        self.client = client
        self.table_name = table_name
        self.table = client.table(table_name)
    
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Find a single record by ID"""
        result = self.table.select("*").eq("id", id).execute()
        return result.data[0] if result.data else None
    
    def find_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all records with optional filters and ordering
        
        Args:
            filters: Dict of column: value pairs to filter by
            order_by: Column name to order by
            order_desc: If True, order descending; if False, ascending
            limit: Maximum number of records to return
            offset: Number of records to skip
        
        Returns:
            List of matching records
        """
        query = self.table.select("*")
        
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        
        if order_by:
            query = query.order(order_by, desc=order_desc)
        
        if limit:
            query = query.limit(limit)
        
        if offset:
            query = query.offset(offset)
        
        result = query.execute()
        return result.data
    
    def find_one(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single record matching filters"""
        query = self.table.select("*")
        for column, value in filters.items():
            query = query.eq(column, value)
        
        result = query.limit(1).execute()
        return result.data[0] if result.data else None
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new record
        
        Args:
            data: Dictionary of column: value pairs
        
        Returns:
            Created record
        """
        # Add id if not present (let DB handle created_at with defaults)
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        
        result = self.table.insert(data).execute()
        return result.data[0] if result.data else None
    
    def update(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a record by ID
        
        Args:
            id: Record ID
            data: Dictionary of column: value pairs to update
        
        Returns:
            Updated record
        """
        result = self.table.update(data).eq("id", id).execute()
        return result.data[0] if result.data else None
    
    def delete(self, id: str) -> bool:
        """
        Delete a record by ID
        
        Args:
            id: Record ID
        
        Returns:
            True if deleted, False otherwise
        """
        result = self.table.delete().eq("id", id).execute()
        return len(result.data) > 0
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching filters
        
        Args:
            filters: Dict of column: value pairs to filter by
        
        Returns:
            Count of matching records
        """
        query = self.table.select("id", count="exact")
        
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        
        result = query.execute()
        return result.count if hasattr(result, 'count') else len(result.data)
    
    def exists(self, filters: Dict[str, Any]) -> bool:
        """Check if a record exists matching filters"""
        return self.find_one(filters) is not None

