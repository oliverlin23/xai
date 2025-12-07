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
    
    def find_one(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single record matching filters"""
        results = self.find_all(filters=filters, limit=1)
        return results[0] if results else None
    
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
        # Only include columns that exist in the sessions table:
        # id, question_text, question_type, created_at, started_at, completed_at,
        # prediction_probability, confidence, total_duration_seconds
        data = {
            "question_text": question_text,
            "question_type": question_type,
            "started_at": datetime.utcnow().isoformat(),
        }
        logger.info(f"[DB] Calling QueryBuilder.create() on 'sessions' table")
        result = self.create(data)
        logger.info(f"[DB] Session created with ID: {result.get('id')}")
        return result
    
    def mark_completed(
        self,
        session_id: str,
        prediction_probability: Optional[float] = None,
        confidence: Optional[float] = None,
        total_duration_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Mark session as completed.
        
        Note: prediction_probability, confidence, and total_duration_seconds are 
        stored in forecaster_responses table, not sessions table.
        These params are kept for API compatibility but ignored.
        
        Args:
            session_id: Session ID
            prediction_probability: (ignored - stored in forecaster_responses)
            confidence: (ignored - stored in forecaster_responses)
            total_duration_seconds: (ignored - stored in forecaster_responses)
        
        Returns:
            Updated session record
        """
        # Only update completed_at - other fields stored in forecaster_responses
        data = {"completed_at": datetime.utcnow().isoformat()}
        return self.update(session_id, data)
    
    def get_session_status(self, session_id: str) -> str:
        """
        Get session status based on completed_at field.
        
        Returns:
            'completed' if completed_at is set, 'running' otherwise
        """
        session = self.find_by_id(session_id)
        if not session:
            return "not_found"
        return "completed" if session.get("completed_at") else "running"


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


class TraderRepository(BaseRepository):
    """Repository for trader_state_live table"""
    
    def __init__(self):
        super().__init__("trader_state_live")
    
    def get_session_traders(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all traders for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of trader records
        """
        return self.find_all(
            filters={"session_id": session_id},
            order_by="name",
            order_desc=False
        )
    
    def get_trader(self, session_id: str, trader_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific trader for a session
        
        Args:
            session_id: Session ID
            trader_name: Trader name
            
        Returns:
            Trader record or None
        """
        return self.find_one({
            "session_id": session_id,
            "name": trader_name
        })
    
    def upsert_trader(
        self, 
        session_id: str, 
        trader_name: str, 
        trader_type: str,
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Create or update a trader record.
        Uses upsert to handle race conditions.
        
        Args:
            session_id: Session ID
            trader_name: Trader name (must match enum value)
            trader_type: Type of trader (fundamental, noise, user)
            system_prompt: System prompt/notes to save
            
        Returns:
            Created or updated trader record
        """
        existing = self.get_trader(session_id, trader_name)
        if existing:
            return self.update(existing["id"], {"system_prompt": system_prompt})
        else:
            return self.create({
                "session_id": session_id,
                "trader_type": trader_type,
                "name": trader_name,
                "system_prompt": system_prompt
            })
    
    def save_system_prompt(
        self, 
        session_id: str, 
        trader_name: str, 
        system_prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        Save/update a trader's system prompt.
        Returns None if trader doesn't exist and cannot be created.
        
        Args:
            session_id: Session ID
            trader_name: Trader name
            system_prompt: System prompt to save
            
        Returns:
            Updated trader record or None
        """
        try:
            existing = self.get_trader(session_id, trader_name)
            if existing:
                result = self.update(existing["id"], {"system_prompt": system_prompt})
                logger.info(f"[DB] Saved system_prompt for {trader_name} ({len(system_prompt)} chars)")
                return result
            else:
                logger.warning(f"[DB] Trader {trader_name} not found in session {session_id}")
                return None
        except Exception as e:
            logger.error(f"[DB] Failed to save system_prompt for {trader_name}: {e}")
            return None


class ForecasterResponseRepository(BaseRepository):
    """Repository for forecaster_responses table"""
    
    def __init__(self):
        super().__init__("forecaster_responses")
    
    def create_response(
        self,
        session_id: str,
        forecaster_class: str,
        status: str = "running"
    ) -> Dict[str, Any]:
        """
        Create a new forecaster response
        
        Args:
            session_id: Session ID
            forecaster_class: Forecaster class/personality (e.g., 'conservative', 'momentum')
            status: Initial status (default: 'running')
        
        Returns:
            Created forecaster response record
        """
        data = {
            "session_id": session_id,
            "forecaster_class": forecaster_class,
            "status": status,
        }
        return self.create(data)
    
    def update_response(
        self,
        response_id: str,
        prediction_result: Optional[Dict[str, Any]] = None,
        prediction_probability: Optional[float] = None,
        confidence: Optional[float] = None,
        total_duration_seconds: Optional[float] = None,
        total_duration_formatted: Optional[str] = None,
        phase_durations: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a forecaster response with prediction results
        
        Args:
            response_id: Response ID
            prediction_result: Full prediction result JSONB
            prediction_probability: Probability of event (0.0-1.0)
            confidence: Confidence in probability estimate (0.0-1.0)
            total_duration_seconds: Total execution time in seconds
            total_duration_formatted: Human-readable duration
            phase_durations: Duration breakdown by phase
            status: Status (running, completed, failed)
            error_message: Error message if failed
        
        Returns:
            Updated response record
        """
        data = {}
        
        if prediction_result is not None:
            data["prediction_result"] = prediction_result
        
        if prediction_probability is not None:
            data["prediction_probability"] = float(prediction_probability)
        
        if confidence is not None:
            data["confidence"] = float(confidence)
        
        if total_duration_seconds is not None:
            data["total_duration_seconds"] = float(total_duration_seconds)
        
        if total_duration_formatted is not None:
            data["total_duration_formatted"] = total_duration_formatted
        
        if phase_durations is not None:
            data["phase_durations"] = phase_durations
        
        if status is not None:
            data["status"] = status
            if status in ["completed", "failed"]:
                data["completed_at"] = datetime.utcnow().isoformat()
        
        if error_message is not None:
            data["error_message"] = error_message
        
        return self.update(response_id, data)
    
    def get_session_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all forecaster responses for a session
        
        Args:
            session_id: Session ID
        
        Returns:
            List of forecaster response records
        """
        return self.find_all(
            filters={"session_id": session_id},
            order_by="created_at",
            order_desc=False
        )
    
    def get_response_by_class(
        self,
        session_id: str,
        forecaster_class: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific forecaster response by class
        
        Args:
            session_id: Session ID
            forecaster_class: Forecaster class
        
        Returns:
            Response record or None
        """
        return self.find_one({
            "session_id": session_id,
            "forecaster_class": forecaster_class
        })

