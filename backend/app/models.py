"""
SQLAlchemy models for Supabase database
"""
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, Text, DECIMAL, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMPTZ
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()


# =============================================================================
# ENUMS (matching 003_create_trading_tables.sql)
# =============================================================================

class TraderTypeEnum(str, enum.Enum):
    FUNDAMENTAL = "fundamental"
    NOISE = "noise"
    USER = "user"


class OrderSideEnum(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatusEnum(str, enum.Enum):
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"


# Valid trader names (for validation, not an enum in SQLAlchemy)
FUNDAMENTAL_TRADERS = {"conservative", "momentum", "historical", "balanced", "realtime"}
NOISE_TRADERS = {
    "eacc_sovereign", "america_first", "blue_establishment", "progressive_left",
    "optimizer_idw", "fintwit_market", "builder_engineering", "academic_research", "osint_intel",
}
USER_TRADERS = {"oliver", "owen", "skylar", "tyler"}
VALID_TRADER_NAMES = FUNDAMENTAL_TRADERS | NOISE_TRADERS | USER_TRADERS


class Session(Base):
    """Forecast session model - now supports multiple forecaster responses"""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False, default="binary")
    status = Column(String(50), nullable=False, default="running")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)


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


# =============================================================================
# TRADING TABLES (from 003_create_trading_tables.sql)
# =============================================================================

class TraderStateLive(Base):
    """Current state of each trader in a session"""
    __tablename__ = "trader_state_live"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    trader_type = Column(SQLEnum(TraderTypeEnum, name="trader_type", create_type=False), nullable=False)
    name = Column(String(50), nullable=False)  # trader_name enum in DB
    system_prompt = Column(Text)
    position = Column(Integer, nullable=False, default=0)
    pnl = Column(DECIMAL(12, 2), nullable=False, default=0)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)


class TraderPromptsHistory(Base):
    """Historical log of all system prompts"""
    __tablename__ = "trader_prompts_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    trader_type = Column(SQLEnum(TraderTypeEnum, name="trader_type", create_type=False), nullable=False)
    name = Column(String(50), nullable=False)
    prompt_number = Column(Integer, nullable=False)
    system_prompt = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class OrderBookLive(Base):
    """Active orders in the order book"""
    __tablename__ = "orderbook_live"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    trader_name = Column(String(50), nullable=False)
    side = Column(SQLEnum(OrderSideEnum, name="order_side", create_type=False), nullable=False)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    filled_quantity = Column(Integer, nullable=False, default=0)
    status = Column(SQLEnum(OrderStatusEnum, name="order_status", create_type=False), nullable=False, default=OrderStatusEnum.OPEN)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class OrderBookHistory(Base):
    """Archived orders"""
    __tablename__ = "orderbook_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    trader_name = Column(String(50), nullable=False)
    side = Column(SQLEnum(OrderSideEnum, name="order_side", create_type=False), nullable=False)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    filled_quantity = Column(Integer, nullable=False, default=0)
    status = Column(SQLEnum(OrderStatusEnum, name="order_status", create_type=False), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class Trade(Base):
    """Matched trades between buyers and sellers"""
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    buyer_name = Column(String(50), nullable=False)
    seller_name = Column(String(50), nullable=False)
    price = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
