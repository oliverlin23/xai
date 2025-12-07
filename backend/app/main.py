"""
FastAPI application entry point for Superforecaster
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import uuid
from app.db import SessionRepository
from app.agents.orchestrator import AgentOrchestrator
from app.core.logging_config import get_logger
import asyncio

logger = get_logger(__name__)
logger.info("=" * 60)
logger.info("Starting Superforecaster API - main.py loaded")
logger.info("=" * 60)

from .market import router as market_router

app = FastAPI(
    title="Superforecaster API",
    description="24-agent superforecasting system powered by Grok AI",
    version="0.1.0"
)

# Include market router
app.include_router(market_router)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class AgentCounts(BaseModel):
    """Agent counts for each phase"""
    phase_1_discovery: int = 10  # Discovery agents
    phase_2_validation: int = 3   # Validation agents (always 3: validator, rater, consensus)
    phase_3_research: int = 10    # Research agents (5 historical + 5 current)
    phase_4_synthesis: int = 1    # Synthesis agent (always 1)


class ForecastRequest(BaseModel):
    question_text: str
    question_type: str = "binary"  # binary, numeric, categorical
    agent_counts: Optional[AgentCounts] = None  # Optional agent counts (defaults to standard 24-agent setup)


class ForecastResponse(BaseModel):
    id: str
    question_text: str
    status: str
    created_at: datetime


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("GET /health - Health check requested")
    return {"status": "healthy", "service": "superforecaster-api"}


async def run_orchestrator(session_id: str, question_text: str, agent_counts: Optional[Dict[str, int]] = None):
    """Run the agent orchestrator in background"""
    logger.info(f"[BACKGROUND TASK] Starting orchestrator for session {session_id}")
    logger.info(f"[BACKGROUND TASK] Question: {question_text[:100]}...")
    if agent_counts:
        logger.info(f"[BACKGROUND TASK] Agent counts: {agent_counts}")
    else:
        logger.info("[BACKGROUND TASK] Using default agent counts (10, 3, 10, 1)")
    
    try:
        logger.info(f"[BACKGROUND TASK] Creating AgentOrchestrator instance")
        orchestrator = AgentOrchestrator(session_id, question_text, agent_counts=agent_counts)
        logger.info(f"[BACKGROUND TASK] Calling orchestrator.run()")
        await orchestrator.run()
        logger.info(f"[BACKGROUND TASK] Orchestrator completed successfully for session {session_id}")
    except Exception as e:
        logger.error(f"[BACKGROUND TASK] Orchestrator failed for session {session_id}: {e}", exc_info=True)


@app.post("/api/forecasts", response_model=ForecastResponse)
async def create_forecast(request: ForecastRequest, background_tasks: BackgroundTasks):
    """
    Create a new forecast session and start agent workflow
    """
    logger.info("=" * 60)
    logger.info("POST /api/forecasts - Creating new forecast")
    logger.info(f"Question: {request.question_text[:100]}...")
    logger.info(f"Question type: {request.question_type}")
    
    # Create session in database
    logger.info("Calling SessionRepository.create_session()")
    session_repo = SessionRepository()
    session = session_repo.create_session(
        question_text=request.question_text,
        question_type=request.question_type
    )
    
    session_id = session["id"]
    logger.info(f"Session created: {session_id}")
    
    # Extract agent counts if provided
    agent_counts = None
    if request.agent_counts:
        logger.info("Agent counts provided in request")
        agent_counts = {
            "phase_1_discovery": request.agent_counts.phase_1_discovery,
            "phase_2_validation": request.agent_counts.phase_2_validation,
            "phase_3_research": request.agent_counts.phase_3_research,
            "phase_4_synthesis": request.agent_counts.phase_4_synthesis,
        }
        logger.info(f"Agent counts: Phase1={agent_counts['phase_1_discovery']}, Phase2={agent_counts['phase_2_validation']}, Phase3={agent_counts['phase_3_research']}, Phase4={agent_counts['phase_4_synthesis']}")
    else:
        logger.info("No agent counts provided, using defaults")
    
    # Start orchestrator in background
    logger.info("Adding orchestrator to background tasks")
    background_tasks.add_task(run_orchestrator, session_id, request.question_text, agent_counts)
    logger.info("=" * 60)

    # Parse created_at (handle both ISO format and string)
    created_at_str = session["created_at"]
    if isinstance(created_at_str, str):
        # Handle ISO format with or without timezone
        created_at_str = created_at_str.replace("Z", "+00:00")
        created_at = datetime.fromisoformat(created_at_str)
    else:
        created_at = datetime.now()
    
    return ForecastResponse(
        id=session_id,
        question_text=request.question_text,
        status="running",
        created_at=created_at
    )


@app.get("/api/forecasts/{forecast_id}")
async def get_forecast(forecast_id: str):
    """
    Get forecast session details including status, result, factors, and agent logs
    """
    logger.info(f"GET /api/forecasts/{forecast_id} - Fetching forecast")
    from app.db import SessionRepository, AgentLogRepository, FactorRepository
    
    logger.info("Initializing repositories: SessionRepository, AgentLogRepository, FactorRepository")
    session_repo = SessionRepository()
    log_repo = AgentLogRepository()
    factor_repo = FactorRepository()
    
    # Get session
    logger.info(f"Calling session_repo.find_by_id({forecast_id})")
    session = session_repo.find_by_id(forecast_id)
    if not session:
        logger.warning(f"Forecast {forecast_id} not found")
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    # Get agent logs
    logger.info(f"Calling log_repo.get_session_logs({forecast_id})")
    agent_logs = log_repo.get_session_logs(forecast_id)
    
    # Get factors
    logger.info(f"Calling factor_repo.get_session_factors({forecast_id})")
    factors = factor_repo.get_session_factors(forecast_id)
    
    logger.info(f"Returning forecast data: {len(agent_logs)} logs, {len(factors)} factors")
    
    # Extract duration and prediction fields - prefer separate columns, fallback to JSONB
    prediction_result = session.get("prediction_result")
    
    # Get total_duration_seconds from column first, then fallback to JSONB
    total_duration_seconds = session.get("total_duration_seconds")
    if total_duration_seconds is None and prediction_result and isinstance(prediction_result, dict):
        total_duration_seconds = prediction_result.get("total_duration_seconds")
    
    # Get prediction_probability and confidence from columns first, then fallback to JSONB
    prediction_probability = session.get("prediction_probability")
    confidence = session.get("confidence")
    if prediction_probability is None and prediction_result and isinstance(prediction_result, dict):
        prediction_probability = prediction_result.get("prediction_probability")
    if confidence is None and prediction_result and isinstance(prediction_result, dict):
        confidence = prediction_result.get("confidence")
    
    # Format duration for display
    total_duration_formatted = None
    phase_durations = None
    if prediction_result and isinstance(prediction_result, dict):
        total_duration_formatted = prediction_result.get("total_duration_formatted")
        phase_durations = prediction_result.get("phase_durations")
    
    # Format response
    response = {
        "id": session["id"],
        "question_text": session["question_text"],
        "question_type": session["question_type"],
        "status": session["status"],
        "current_phase": session.get("current_phase"),
        "prediction_result": prediction_result,
        "factors": factors,
        "agent_logs": agent_logs,
        "total_cost_tokens": session.get("total_cost_tokens", 0),
        "created_at": session["created_at"],
        "completed_at": session.get("completed_at")
    }
    
    # Add duration fields if available
    if total_duration_seconds is not None:
        response["total_duration_seconds"] = float(total_duration_seconds) if total_duration_seconds else None
        response["total_duration_formatted"] = total_duration_formatted
    if phase_durations:
        response["phase_durations"] = phase_durations
    
    # Add prediction_probability and confidence if available (from columns or JSONB)
    if prediction_probability is not None:
        response["prediction_probability"] = float(prediction_probability) if prediction_probability else None
    if confidence is not None:
        response["confidence"] = float(confidence) if confidence else None
    
    return response


@app.get("/api/forecasts")
async def list_forecasts(limit: int = 10, offset: int = 0, question_text: Optional[str] = None):
    """
    List all past forecast sessions, optionally filtered by question_text
    """
    logger.info(f"GET /api/forecasts - Listing forecasts (limit={limit}, offset={offset})")
    from app.db import SessionRepository
    
    logger.info("Initializing SessionRepository")
    session_repo = SessionRepository()
    
    # Build filters
    filters = {}
    if question_text:
        filters["question_text"] = question_text
        logger.info(f"Filtering by question_text: {question_text[:50]}...")
    
    # Get sessions ordered by created_at descending
    sessions = session_repo.find_all(
        filters=filters if filters else None,
        order_by="created_at",
        order_desc=True,
        limit=limit,
        offset=offset
    )
    
    # Get total count
    total = session_repo.count(filters=filters if filters else None)
    
    return {
        "forecasts": sessions,
        "total": total
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
