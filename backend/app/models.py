"""
SQLAlchemy models for Supabase database
"""
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, Text, DECIMAL, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class Session(Base):
    """Forecast session model"""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False, default="binary")
    status = Column(String(50), nullable=False, default="running")
    current_phase = Column(String(50))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    prediction_result = Column(JSONB)
    total_cost_tokens = Column(Integer, default=0)


class AgentLog(Base):
    """Agent execution log model"""
    __tablename__ = "agent_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    phase = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="running")
    output_data = Column(JSONB)
    error_message = Column(Text)
    tokens_used = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP)


class Factor(Base):
    """Discovered factor model"""
    __tablename__ = "factors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    importance_score = Column(DECIMAL(4, 2))
    research_summary = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
