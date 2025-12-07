"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# Agent Output Schemas
class FactorDiscoveryOutput(BaseModel):
    """Output schema for discovery agents (Phase 1)"""
    factors: List[Dict[str, str]] = Field(
        description="List of discovered factors with name, description, category"
    )


class FactorValidationOutput(BaseModel):
    """Output schema for validation agent (Phase 2, Agent 11)"""
    validated_factors: List[Dict[str, str]] = Field(
        description="Deduplicated and validated factors"
    )


class FactorRatingOutput(BaseModel):
    """Output schema for rating agent (Phase 2, Agent 12)"""
    rated_factors: List[Dict[str, Any]] = Field(
        description="Factors with importance scores (1-10)"
    )


class ConsensusOutput(BaseModel):
    """Output schema for consensus agent (Phase 2, Agent 13)"""
    top_factors: List[Dict[str, Any]] = Field(
        description="Top 5 factors selected for deep research"
    )


class RatingConsensusOutput(BaseModel):
    """Output schema for merged rating+consensus agent (Phase 2, Agents 12+13 combined)"""
    rated_factors: List[Dict[str, Any]] = Field(
        description="All factors with importance scores (1-10)"
    )
    top_factors: List[Dict[str, Any]] = Field(
        description="Top 5 factors selected for deep research (must be subset of rated_factors)"
    )


class HistoricalResearchOutput(BaseModel):
    """Output schema for historical research agents (Phase 3, Agents 14-18)"""
    factor_name: str
    historical_analysis: str
    sources: List[str]
    confidence: float = Field(ge=0.0, le=1.0)


class CurrentDataOutput(BaseModel):
    """Output schema for current data research agents (Phase 3, Agents 19-23)"""
    factor_name: str
    current_findings: str
    sources: List[str]
    confidence: float = Field(ge=0.0, le=1.0)


class PredictionOutput(BaseModel):
    """Output schema for synthesis agent (Phase 4, Agent 24)"""
    prediction: str = Field(description="Binary choice (exactly one of the two options provided)")
    prediction_probability: float = Field(
        ge=0.0, 
        le=1.0,
        description="Probability of the event occurring (0.0-1.0). This is the actual forecast probability."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the prediction_probability estimate (0.0-1.0). Based on evidence quality, thoroughness, and consistency."
    )
    reasoning: str
    key_factors: List[str]


# API Schemas
class ForecastCreate(BaseModel):
    """Request schema for creating a forecast"""
    question_text: str
    question_type: str = "binary"


class FactorSchema(BaseModel):
    """Schema for factor representation"""
    id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    importance_score: Optional[Decimal]
    research_summary: Optional[str]


class AgentLogSchema(BaseModel):
    """Schema for agent log representation"""
    id: str
    agent_name: str
    phase: str
    status: str
    output_data: Optional[Dict[str, Any]]
    tokens_used: int
    created_at: datetime
    completed_at: Optional[datetime]


class ForecastResponse(BaseModel):
    """Response schema for forecast details"""
    id: str
    question_text: str
    question_type: str
    status: str  # Inferred from completed_at: "running" if None, "completed" otherwise
    prediction_result: Optional[Dict[str, Any]]
    factors: List[FactorSchema]
    agent_logs: List[AgentLogSchema]
    created_at: datetime
    completed_at: Optional[datetime]
    # Optional fields from forecaster_responses
    prediction_probability: Optional[float] = None
    confidence: Optional[float] = None
    total_duration_seconds: Optional[float] = None
    total_duration_formatted: Optional[str] = None
    forecaster_responses: Optional[List[Dict[str, Any]]] = None
