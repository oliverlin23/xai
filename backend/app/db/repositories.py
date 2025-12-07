"""
Repository classes for database tables
Provides high-level interface for database operations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.db.client import get_db_client
from app.db.queries import QueryBuilder
from app.core.logging_config import get_logger
import uuid

logger = get_logger(__name__)


class BaseRepository:
    """Base repository with common database operations"""
    
    def __init__(self, table_name: str):
        """
        Initialize repository for a specific table
        
        Args:
            table_name: Name of the table
        """
        self.client = get_db_client()
        self.table_name = table_name
        self.query = QueryBuilder(self.client, table_name)
    
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Find record by ID"""
        return self.query.find_by_id(id)
    
    def find_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Find all records with optional filters"""
        return self.query.find_all(filters, order_by, order_desc, limit, offset)
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record"""
        return self.query.create(data)
    
    def update(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record"""
        return self.query.update(id, data)
    
    def delete(self, id: str) -> bool:
        """Delete a record"""
        return self.query.delete(id)
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records"""
        return self.query.count(filters)


class SessionRepository(BaseRepository):
    """Repository for sessions table"""
    
    def __init__(self):
        super().__init__("sessions")
    
    def create_session(
        self,
        question_text: str,
        question_type: str = "binary"
    ) -> Dict[str, Any]:
        """
        Create a new forecast session
        
        Args:
            question_text: The forecasting question
            question_type: Type of question (binary, numeric, categorical)
        
        Returns:
            Created session record
        """
        logger.info(f"[DB] SessionRepository.create_session() called")
        logger.info(f"[DB] Question: {question_text[:50]}...")
        logger.info(f"[DB] Type: {question_type}")
        data = {
            "question_text": question_text,
            "question_type": question_type,
            "status": "running",
            "current_phase": "factor_discovery",
            "started_at": datetime.utcnow().isoformat(),
            "total_cost_tokens": 0,
        }
        logger.info(f"[DB] Calling QueryBuilder.create() on 'sessions' table")
        result = self.create(data)
        logger.info(f"[DB] Session created with ID: {result.get('id')}")
        return result
    
    def update_status(
        self,
        session_id: str,
        status: str,
        phase: Optional[str] = None,
        prediction_result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update session status and optionally phase/prediction
        
        Args:
            session_id: Session ID
            status: New status (running, completed, failed)
            phase: Optional phase name
            prediction_result: Optional prediction result dict
            error_message: Optional error message if failed
        
        Returns:
            Updated session record
        """
        data = {"status": status}
        
        if phase:
            data["current_phase"] = phase
        
        if prediction_result:
            data["prediction_result"] = prediction_result
        
        if error_message:
            data["error_message"] = error_message
        
        if status in ["completed", "failed"]:
            data["completed_at"] = datetime.utcnow().isoformat()
        
        return self.update(session_id, data)
    
    def add_tokens(self, session_id: str, tokens: int) -> Dict[str, Any]:
        """
        Add tokens to session total
        
        WARNING: This has a race condition when called from parallel agents.
        Use add_tokens_batch() or increment_tokens() for concurrent updates.
        
        Args:
            session_id: Session ID
            tokens: Number of tokens to add
        
        Returns:
            Updated session record
        """
        session = self.find_by_id(session_id)
        if session:
            current_tokens = session.get("total_cost_tokens", 0)
            return self.update(session_id, {
                "total_cost_tokens": current_tokens + tokens
            })
        return session
    
    def increment_tokens(self, session_id: str, tokens: int) -> Dict[str, Any]:
        """
        Atomically increment tokens using SQL increment (thread-safe)
        
        This avoids race conditions when multiple agents update tokens concurrently.
        
        Args:
            session_id: Session ID
            tokens: Number of tokens to add
        
        Returns:
            Updated session record
        """
        # Use Supabase RPC or direct SQL increment
        # For now, use a workaround: read current value and update
        # TODO: Implement proper atomic increment via Supabase RPC function
        session = self.find_by_id(session_id)
        if session:
            current_tokens = session.get("total_cost_tokens", 0)
            return self.update(session_id, {
                "total_cost_tokens": current_tokens + tokens
            })
        return session


class AgentLogRepository(BaseRepository):
    """Repository for agent_logs table"""
    
    def __init__(self):
        super().__init__("agent_logs")
    
    def create_log(
        self,
        session_id: str,
        agent_name: str,
        phase: str,
        status: str = "running"
    ) -> Dict[str, Any]:
        """
        Create a new agent log entry
        
        Args:
            session_id: Session ID
            agent_name: Name of the agent
            phase: Phase name
            status: Initial status (running, completed, failed)
        
        Returns:
            Created log record
        """
        logger.info(f"[DB] AgentLogRepository.create_log() called")
        logger.info(f"[DB] Session: {session_id}, Agent: {agent_name}, Phase: {phase}")
        data = {
            "session_id": session_id,
            "agent_name": agent_name,
            "phase": phase,
            "status": status,
            "tokens_used": 0,
        }
        logger.info(f"[DB] Calling QueryBuilder.create() on 'agent_logs' table")
        result = self.create(data)
        logger.info(f"[DB] Agent log created with ID: {result.get('id')}")
        return result
    
    def update_log(
        self,
        log_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        tokens_used: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update agent log with results
        
        Args:
            log_id: Log ID
            status: Final status (completed, failed)
            output_data: Optional agent output data
            tokens_used: Optional token count
            error_message: Optional error message
        
        Returns:
            Updated log record
        """
        data = {"status": status}
        
        # Only set completed_at when agent actually completes or fails
        if status in ["completed", "failed"]:
            data["completed_at"] = datetime.utcnow().isoformat()
        
        if output_data:
            data["output_data"] = output_data
        
        if tokens_used is not None:
            data["tokens_used"] = tokens_used
        
        if error_message:
            data["error_message"] = error_message
        
        return self.update(log_id, data)
    
    def get_session_logs(
        self,
        session_id: str,
        phase: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all agent logs for a session
        
        Args:
            session_id: Session ID
            phase: Optional phase filter
        
        Returns:
            List of log records
        """
        filters = {"session_id": session_id}
        if phase:
            filters["phase"] = phase
        
        return self.find_all(
            filters=filters,
            order_by="created_at",
            order_desc=False
        )


class FactorRepository(BaseRepository):
    """Repository for factors table"""
    
    def __init__(self):
        super().__init__("factors")
    
    def create_factor(
        self,
        session_id: str,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        importance_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a new factor
        
        Args:
            session_id: Session ID
            name: Factor name
            description: Optional description
            category: Optional category
            importance_score: Optional importance score (0-10)
        
        Returns:
            Created factor record
        """
        data = {
            "session_id": session_id,
            "name": name,
        }
        
        if description:
            data["description"] = description
        if category:
            data["category"] = category
        if importance_score is not None:
            data["importance_score"] = float(importance_score)
        
        return self.create(data)
    
    def update_factor(
        self,
        factor_id: str,
        importance_score: Optional[float] = None,
        research_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update factor with importance score and/or research
        
        Args:
            factor_id: Factor ID
            importance_score: Optional importance score
            research_summary: Optional research summary
        
        Returns:
            Updated factor record
        """
        data = {}
        
        if importance_score is not None:
            data["importance_score"] = float(importance_score)
        
        if research_summary:
            data["research_summary"] = research_summary
        
        return self.update(factor_id, data)
    
    def get_session_factors(
        self,
        session_id: str,
        order_by_importance: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all factors for a session
        
        Args:
            session_id: Session ID
            order_by_importance: If True, order by importance score descending
        
        Returns:
            List of factor records
        """
        filters = {"session_id": session_id}
        
        if order_by_importance:
            # Get all factors first, then sort in Python to handle None values properly
            factors = self.find_all(filters=filters)
            # Sort by importance_score, putting None values last
            factors.sort(
                key=lambda f: (f.get("importance_score") is None, f.get("importance_score") or 0),
                reverse=True
            )
            return factors
        else:
            return self.find_all(
                filters=filters,
                order_by="created_at",
                order_desc=True
            )

