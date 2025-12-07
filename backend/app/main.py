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

app = FastAPI(
    title="Superforecaster API",
    description="24-agent superforecasting system powered by Grok AI",
    version="0.1.0"
)

# CORS configuration for local development
# Allow common localhost origins to prevent ERR_EMPTY_RESPONSE / CORS failures in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class AgentCounts(BaseModel):
    """Agent counts for each phase"""
    phase_1_discovery: Optional[int] = None  # Discovery agents
    phase_2_validation: Optional[int] = None  # Validation agents (always 2: validator, rating_consensus)
    phase_3_research: Optional[int] = None  # Research agents (backward compatibility - will split 50/50 if phase_3_historical/current not provided)
    phase_3_historical: Optional[int] = None  # Historical research agents
    phase_3_current: Optional[int] = None  # Current research agents
    phase_4_synthesis: Optional[int] = None  # Synthesis agent (always 1)


class ForecastRequest(BaseModel):
    question_text: str
    question_type: str = "binary"  # binary, numeric, categorical
    agent_counts: Optional[AgentCounts] = None  # Optional agent counts (defaults to standard 24-agent setup)
    forecaster_class: str = "balanced"  # One of: "conservative", "momentum", "historical", "realtime", "balanced"
    run_all_forecasters: bool = False  # If True, run all 5 forecaster personalities in parallel (for Cassandra)


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


async def run_orchestrator(session_id: str, question_text: str, agent_counts: Optional[Dict[str, int]] = None, forecaster_class: str = "balanced"):
    """Run the agent orchestrator in background for a specific forecaster class"""
    logger.info(f"[BACKGROUND TASK] Starting orchestrator for session {session_id}, forecaster_class: {forecaster_class}")
    logger.info(f"[BACKGROUND TASK] Question: {question_text[:100]}...")
    if agent_counts:
        logger.info(f"[BACKGROUND TASK] Agent counts: {agent_counts}")
    else:
        logger.info(f"[BACKGROUND TASK] Using default agent counts for {forecaster_class}")
    logger.info(f"[BACKGROUND TASK] Forecaster class: {forecaster_class}")
    
    try:
        logger.info(f"[BACKGROUND TASK] Creating AgentOrchestrator instance for {forecaster_class}")
        orchestrator = AgentOrchestrator(session_id, question_text, agent_counts=agent_counts, forecaster_class=forecaster_class)
        logger.info(f"[BACKGROUND TASK] Calling orchestrator.run() for {forecaster_class}")
        await orchestrator.run()
        logger.info(f"[BACKGROUND TASK] Orchestrator completed successfully for session {session_id}, forecaster_class: {forecaster_class}")
    except Exception as e:
        logger.error(f"[BACKGROUND TASK] Orchestrator failed for session {session_id}, forecaster_class {forecaster_class}: {e}", exc_info=True)


async def run_all_forecasters(session_id: str, question_text: str, agent_counts: Optional[Dict[str, int]] = None):
    """Run all 5 forecaster personalities in parallel for a session"""
    from app.agents.prompts import FORECASTER_CLASSES
    
    forecaster_classes = list(FORECASTER_CLASSES.keys())  # ['conservative', 'momentum', 'historical', 'realtime', 'balanced']
    logger.info(f"[BACKGROUND TASK] Running all {len(forecaster_classes)} forecaster classes in parallel for session {session_id}")
    logger.info(f"[BACKGROUND TASK] Forecaster classes: {forecaster_classes}")
    
    # Run all orchestrators in parallel
    tasks = [
        run_orchestrator(session_id, question_text, agent_counts, fc)
        for fc in forecaster_classes
    ]
    
    # Use asyncio.gather to run all in parallel, but don't fail all if one fails
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Log results
    for i, result in enumerate(results):
        fc = forecaster_classes[i]
        if isinstance(result, Exception):
            logger.error(f"[BACKGROUND TASK] Forecaster {fc} failed: {result}")
        else:
            logger.info(f"[BACKGROUND TASK] Forecaster {fc} completed successfully")
    
    logger.info(f"[BACKGROUND TASK] All forecasters completed for session {session_id}")


@app.post("/api/forecasts", response_model=ForecastResponse)
async def create_forecast(request: ForecastRequest, background_tasks: BackgroundTasks):
    """
    Create a new forecast session and start agent workflow
    """
    logger.info("=" * 60)
    logger.info("POST /api/forecasts - Creating new forecast")
    logger.info(f"Question: {request.question_text[:100]}...")
    logger.info(f"Question type: {request.question_type}")
    logger.info(f"Run all forecasters: {request.run_all_forecasters}")
    
    # Validate forecaster_class if not running all
    from app.agents.prompts import FORECASTER_CLASSES
    if not request.run_all_forecasters:
        if request.forecaster_class not in FORECASTER_CLASSES:
            logger.warning(f"Invalid forecaster_class '{request.forecaster_class}', defaulting to 'balanced'")
            forecaster_class = "balanced"
        else:
            forecaster_class = request.forecaster_class
        logger.info(f"Forecaster class: {forecaster_class}")
    
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
        agent_counts = {}
        if request.agent_counts.phase_1_discovery is not None:
            agent_counts["phase_1_discovery"] = request.agent_counts.phase_1_discovery
        if request.agent_counts.phase_2_validation is not None:
            agent_counts["phase_2_validation"] = request.agent_counts.phase_2_validation
        # Support new separate historical/current counts
        if request.agent_counts.phase_3_historical is not None:
            agent_counts["phase_3_historical"] = request.agent_counts.phase_3_historical
        if request.agent_counts.phase_3_current is not None:
            agent_counts["phase_3_current"] = request.agent_counts.phase_3_current
        # Backward compatibility: if phase_3_research provided but not historical/current, use it
        if request.agent_counts.phase_3_research is not None and "phase_3_historical" not in agent_counts:
            agent_counts["phase_3_research"] = request.agent_counts.phase_3_research
        if request.agent_counts.phase_4_synthesis is not None:
            agent_counts["phase_4_synthesis"] = request.agent_counts.phase_4_synthesis
        
        logger.info(f"Agent counts: {agent_counts}")
    else:
        if request.run_all_forecasters:
            logger.info("No agent counts provided, each forecaster will use its own defaults")
        else:
            logger.info("No agent counts provided, using forecaster class defaults")
    
    # Determine which forecasters to run
    if request.run_all_forecasters:
        # Run all 5 forecaster personalities in parallel (for Cassandra)
        # Each will create its own forecaster_response record
        logger.info("Starting all 5 forecaster personalities in parallel")
        logger.info("Forecaster classes: conservative, momentum, historical, realtime, balanced")
        background_tasks.add_task(run_all_forecasters, session_id, request.question_text, agent_counts)
    else:
        # Run single forecaster (for superforecast tab)
        logger.info(f"Starting single forecaster: {forecaster_class}")
        background_tasks.add_task(run_orchestrator, session_id, request.question_text, agent_counts, forecaster_class)
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
    from app.db.repositories import ForecasterResponseRepository
    
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
    
    # Get forecaster responses for this session
    logger.info(f"Fetching forecaster responses for session {forecast_id}")
    response_repo = ForecasterResponseRepository()
    forecaster_responses = response_repo.get_session_responses(forecast_id)
    
    # For backward compatibility, use the first (or most recent) response if available
    # In the future, the frontend should handle multiple responses
    primary_response = None
    if forecaster_responses:
        # Prefer completed responses, then by creation time
        completed_responses = [r for r in forecaster_responses if r.get("status") == "completed"]
        if completed_responses:
            primary_response = completed_responses[0]  # Could sort by created_at if needed
        else:
            primary_response = forecaster_responses[0]
    
    # Extract prediction data from primary response
    prediction_result = None
    total_duration_seconds = None
    prediction_probability = None
    confidence = None
    total_duration_formatted = None
    phase_durations = None
    
    if primary_response:
        prediction_result = primary_response.get("prediction_result")
        total_duration_seconds = primary_response.get("total_duration_seconds")
        prediction_probability = primary_response.get("prediction_probability")
        confidence = primary_response.get("confidence")
        total_duration_formatted = primary_response.get("total_duration_formatted")
        phase_durations = primary_response.get("phase_durations")
    
    # Format response
    # Note: status is inferred from completed_at, not stored in DB
    status = "completed" if session.get("completed_at") else "running"
    
    response = {
        "id": session["id"],
        "question_text": session["question_text"],
        "question_type": session["question_type"],
        "status": status,
        "prediction_result": prediction_result,
        "factors": factors,
        "agent_logs": agent_logs,
        "created_at": session["created_at"],
        "completed_at": session.get("completed_at"),
        "forecaster_responses": forecaster_responses  # Include all responses for future use
    }
    
    # Add duration fields if available
    if total_duration_seconds is not None:
        response["total_duration_seconds"] = float(total_duration_seconds) if total_duration_seconds else None
        response["total_duration_formatted"] = total_duration_formatted
    if phase_durations:
        response["phase_durations"] = phase_durations
    
    # Add prediction_probability and confidence if available
    if prediction_probability is not None:
        response["prediction_probability"] = float(prediction_probability) if prediction_probability else None
    if confidence is not None:
        response["confidence"] = float(confidence) if confidence else None
    
    return response


class RunSessionRequest(BaseModel):
    """Request model for running a session"""
    question_text: str
    question_type: str = "binary"  # binary, numeric, categorical
    agent_counts: Optional[AgentCounts] = None  # Optional agent counts for superforecasters
    resolution_criteria: str = "Standard YES/NO resolution based on outcome occurrence."
    resolution_date: str = "Not specified"
    trading_interval_seconds: int = 10  # Interval between trading rounds


class RunSessionResponse(BaseModel):
    """Response model for run session endpoint"""
    session_id: str
    question_text: str
    status: str
    message: str
    created_at: datetime


async def run_trading_simulation_background(
    session_id: str,
    question_text: str,
    resolution_criteria: str,
    resolution_date: str,
    agent_counts: Optional[Dict[str, int]],
    interval_seconds: int,
):
    """
    Background task that:
    1. Runs superforecasters to seed fundamental trader system_prompts
    2. Stores their predictions in trader_state_live
    3. Places initial market making orders
    4. Starts continuous trading simulation with 18 agents
    """
    import re
    from app.db.repositories import ForecasterResponseRepository, TraderRepository
    from app.market import SupabaseMarketMaker
    from app.traders.simulation import TradingSimulation, register_simulation, unregister_simulation
    
    logger.info(f"[BACKGROUND] Starting trading simulation for session {session_id}")
    
    try:
        trader_repo = TraderRepository()
        market_maker = SupabaseMarketMaker()
        
        # Check if fundamental traders already exist (copied from previous session)
        existing_traders = trader_repo.get_session_traders(session_id)
        fundamental_traders_exist = any(
            t.get("trader_type") == "fundamental" and t.get("system_prompt")
            for t in existing_traders
        )
        
        if fundamental_traders_exist:
            logger.info("[BACKGROUND] Found existing fundamental traders with system_prompts - skipping superforecaster run")
            logger.info("[BACKGROUND] Using existing trader_state_live data from previous session")
        else:
            # Step 1: Run all 5 superforecasters to seed fundamental trader knowledge
            logger.info("[BACKGROUND] Running superforecasters to seed fundamental traders...")
            await run_all_forecasters(session_id, question_text, agent_counts)
            logger.info("[BACKGROUND] Superforecasters completed")
        
        # Step 2: Store forecaster responses as system_prompt in trader_state_live (if we ran forecasters)
        # OR use existing traders and place market making orders
        response_repo = ForecasterResponseRepository()
        forecaster_responses = response_repo.get_session_responses(session_id)
        
        if fundamental_traders_exist:
            # Use existing traders - extract probability from system_prompt for market making
            logger.info("[BACKGROUND] Placing market making orders based on existing trader system_prompts")
            orders_placed = 0
            for trader in existing_traders:
                if trader.get("trader_type") == "fundamental" and trader.get("system_prompt"):
                    # Try to extract probability from system_prompt
                    system_prompt = trader.get("system_prompt", "")
                    trader_name = trader.get("name")
                    
                    # Look for "Probability: X%" pattern in system_prompt (handles both "65.0%" and "65%")
                    prob_match = re.search(r"Probability:\s*([\d.]+)%", system_prompt)
                    if prob_match:
                        try:
                            probability_percent = float(prob_match.group(1))
                            prediction_cents = max(2, min(98, int(round(probability_percent))))
                            
                            result = market_maker.place_market_making_orders(
                                session_id=session_id,
                                trader_name=trader_name,
                                prediction=prediction_cents,
                                spread=4,
                                quantity=100
                            )
                            
                            if result.get("error"):
                                logger.warning(f"[BACKGROUND] Failed to place orders for {trader_name}: {result['error']}")
                            else:
                                orders_placed += 1
                                trades_count = result.get("trades_count", 0)
                                logger.info(
                                    f"[BACKGROUND] Placed market making orders for {trader_name} at {prediction_cents} cents "
                                    f"(matched {trades_count} trades, volume={result.get('volume', 0)})"
                                )
                        except (ValueError, TypeError) as e:
                            logger.warning(f"[BACKGROUND] Failed to parse probability for {trader_name}: {e}")
                    else:
                        logger.warning(f"[BACKGROUND] Could not extract probability from system_prompt for {trader_name}")
            
            logger.info(f"[BACKGROUND] Placed market making orders for {orders_placed} fundamental traders")
            logger.info("[BACKGROUND] Orderbook and trades should now be populated - trading simulation will continue")
        else:
            # Normal flow: process forecaster responses
            logger.info(f"[BACKGROUND] Storing {len(forecaster_responses)} forecaster responses in trader_state_live")
            
            for response in forecaster_responses:
                forecaster_class = response.get("forecaster_class")
                prediction_result = response.get("prediction_result", {})
                
                if forecaster_class and prediction_result:
                    # Build system_prompt from prediction result
                    system_prompt_parts = []
                    
                    if prediction_result.get("prediction"):
                        system_prompt_parts.append(f"Prediction: {prediction_result['prediction']}")
                    
                    prediction_probability = prediction_result.get("prediction_probability")
                    if prediction_probability is not None:
                        system_prompt_parts.append(f"Probability: {prediction_probability:.1%}")
                    
                    if prediction_result.get("confidence") is not None:
                        conf = prediction_result['confidence']
                        system_prompt_parts.append(f"Confidence: {conf:.1%}")
                    
                    if prediction_result.get("reasoning"):
                        system_prompt_parts.append(f"\nReasoning:\n{prediction_result['reasoning']}")
                    
                    if prediction_result.get("key_factors"):
                        factors = prediction_result['key_factors']
                        if isinstance(factors, list):
                            factors_str = "\n".join(f"- {f}" for f in factors)
                            system_prompt_parts.append(f"\nKey Factors:\n{factors_str}")
                    
                    system_prompt = "\n".join(system_prompt_parts)
                    
                    # Create or update trader_state_live record
                    existing_trader = trader_repo.get_trader(session_id, forecaster_class)
                    if existing_trader:
                        trader_repo.update(existing_trader["id"], {"system_prompt": system_prompt})
                    else:
                        trader_repo.create({
                            "session_id": session_id,
                            "trader_type": "fundamental",
                            "name": forecaster_class,
                            "system_prompt": system_prompt
                        })
                    
                    # Place initial market making orders
                    if prediction_probability is not None:
                        prediction_cents = max(2, min(98, int(round(prediction_probability * 100))))
                        market_maker.place_market_making_orders(
                            session_id=session_id,
                            trader_name=forecaster_class,
                            prediction=prediction_cents,
                            spread=4,
                            quantity=100
                        )
        
        # Step 3: Create and start the trading simulation
        logger.info("[BACKGROUND] Starting continuous trading simulation with 18 agents")
        simulation = TradingSimulation(
            session_id=session_id,
            question_text=question_text,
            resolution_criteria=resolution_criteria,
            resolution_date=resolution_date,
        )
        
        # Register simulation in global registry
        register_simulation(simulation)
        
        # Initialize agents
        await simulation.initialize_agents()
        
        # Start continuous trading and track the task for cancellation
        await simulation.run_continuous(interval_seconds=interval_seconds)
        
    except Exception as e:
        logger.error(f"[BACKGROUND] Trading simulation failed for session {session_id}: {e}", exc_info=True)
    finally:
        # Clean up both registries
        unregister_simulation(session_id)
        from app.traders.simulation import clear_session_initializing
        clear_session_initializing(session_id)
        logger.info(f"[BACKGROUND] Trading simulation ended for session {session_id}")


@app.post("/api/sessions/run", response_model=RunSessionResponse)
async def run_session(request: RunSessionRequest, background_tasks: BackgroundTasks):
    """
    Create a new session and start trading simulation in background.
    
    This endpoint returns immediately after creating the session.
    The background task:
    1. Runs 5 superforecasters to seed fundamental trader knowledge
    2. Starts continuous trading simulation with 18 agents
    
    Frontend can see trades in real-time via Supabase realtime subscriptions.
    """
    logger.info("=" * 60)
    logger.info("POST /api/sessions/run - Starting trading simulation")
    logger.info(f"Question: {request.question_text[:100]}...")
    logger.info(f"Question type: {request.question_type}")
    logger.info(f"Trading interval: {request.trading_interval_seconds}s")
    
    # Check if a session with the same question_text already exists
    from app.db.repositories import TraderRepository
    
    session_repo = SessionRepository()
    trader_repo = TraderRepository()
    
    # Find existing sessions with the same question_text
    existing_sessions = session_repo.find_all(
        filters={"question_text": request.question_text},
        order_by="created_at",
        order_desc=True,
        limit=1
    )
    
    # Create session in database
    session = session_repo.create_session(
        question_text=request.question_text,
        question_type=request.question_type
    )
    
    session_id = session["id"]
    logger.info(f"Session created: {session_id}")
    
    # If a previous session exists, copy trader_state_live data from it
    if existing_sessions:
        previous_session_id = existing_sessions[0]["id"]
        logger.info(f"Found previous session with same question_text: {previous_session_id}")
        logger.info("Loading trader_state_live data from previous session...")
        
        # Get all traders from the previous session
        previous_traders = trader_repo.get_session_traders(previous_session_id)
        logger.info(f"Found {len(previous_traders)} traders in previous session")
        
        # Copy each trader's data to the new session (excluding position and pnl which should start fresh)
        for trader in previous_traders:
            # Only copy system_prompt and trader metadata, reset position and pnl
            trader_repo.create({
                "session_id": session_id,
                "trader_type": trader.get("trader_type"),
                "name": trader.get("name"),
                "system_prompt": trader.get("system_prompt"),
                "position": 0,  # Start fresh
                "pnl": 0  # Start fresh
            })
            logger.info(f"Copied trader {trader.get('name')} system_prompt to new session")
        
        logger.info(f"Successfully copied {len(previous_traders)} trader states from previous session")
        
        # Copy orderbook_live records to orderbook_history for the new session
        from app.db.repositories import BaseRepository
        orderbook_repo = BaseRepository("orderbook_live")
        orderbook_history_repo = BaseRepository("orderbook_history")
        trades_repo = BaseRepository("trades")
        
        # Get all orderbook_live records from previous session
        previous_orders = orderbook_repo.find_all(
            filters={"session_id": previous_session_id},
            order_by="created_at",
            order_desc=False
        )
        logger.info(f"Found {len(previous_orders)} orderbook records in previous session")
        
        # Copy orders to orderbook_history for the new session
        orders_copied = 0
        for order in previous_orders:
            try:
                orderbook_history_repo.create({
                    "session_id": session_id,
                    "trader_name": order.get("trader_name"),
                    "side": order.get("side"),
                    "price": order.get("price"),
                    "quantity": order.get("quantity"),
                    "filled_quantity": order.get("filled_quantity"),
                    "status": order.get("status"),
                    "created_at": order.get("created_at")  # Preserve original timestamp
                })
                orders_copied += 1
            except Exception as e:
                logger.warning(f"Failed to copy order {order.get('id')}: {e}")
        
        logger.info(f"Copied {orders_copied} orderbook records to orderbook_history")
        
        # Get all trades from previous session
        previous_trades = trades_repo.find_all(
            filters={"session_id": previous_session_id},
            order_by="created_at",
            order_desc=False
        )
        logger.info(f"Found {len(previous_trades)} trades in previous session")
        
        # Copy trades to the new session (so graph shows history)
        trades_copied = 0
        for trade in previous_trades:
            try:
                trades_repo.create({
                    "session_id": session_id,
                    "buyer_name": trade.get("buyer_name"),
                    "seller_name": trade.get("seller_name"),
                    "price": trade.get("price"),
                    "quantity": trade.get("quantity"),
                    "created_at": trade.get("created_at")  # Preserve original timestamp
                })
                trades_copied += 1
            except Exception as e:
                logger.warning(f"Failed to copy trade {trade.get('id')}: {e}")
        
        logger.info(f"Copied {trades_copied} trades to new session (graph will show history)")
    else:
        logger.info("No previous session found with same question_text, starting fresh")
    
    # Extract agent counts if provided
    agent_counts = None
    if request.agent_counts:
        agent_counts = {}
        if request.agent_counts.phase_1_discovery is not None:
            agent_counts["phase_1_discovery"] = request.agent_counts.phase_1_discovery
        if request.agent_counts.phase_2_validation is not None:
            agent_counts["phase_2_validation"] = request.agent_counts.phase_2_validation
        if request.agent_counts.phase_3_historical is not None:
            agent_counts["phase_3_historical"] = request.agent_counts.phase_3_historical
        if request.agent_counts.phase_3_current is not None:
            agent_counts["phase_3_current"] = request.agent_counts.phase_3_current
        if request.agent_counts.phase_3_research is not None and "phase_3_historical" not in agent_counts:
            agent_counts["phase_3_research"] = request.agent_counts.phase_3_research
        if request.agent_counts.phase_4_synthesis is not None:
            agent_counts["phase_4_synthesis"] = request.agent_counts.phase_4_synthesis
    
    # Mark session as initializing BEFORE starting background task
    # This ensures status endpoint returns "initializing" immediately
    from app.traders.simulation import mark_session_initializing
    mark_session_initializing(session_id)
    
    # Start trading simulation in background
    background_tasks.add_task(
        run_trading_simulation_background,
        session_id,
        request.question_text,
        request.resolution_criteria,
        request.resolution_date,
        agent_counts,
        request.trading_interval_seconds,
    )
    
    logger.info(f"Trading simulation started in background for session {session_id}")
    logger.info("=" * 60)
    
    # Parse created_at
    created_at_str = session["created_at"]
    if isinstance(created_at_str, str):
        created_at_str = created_at_str.replace("Z", "+00:00")
        created_at = datetime.fromisoformat(created_at_str)
    else:
        created_at = datetime.now()
    
    return RunSessionResponse(
        session_id=session_id,
        question_text=request.question_text,
        status="running",
        message="Trading simulation started. 5 superforecasters will run first, then 18 agents will trade continuously.",
        created_at=created_at,
    )


class SimulationStatusResponse(BaseModel):
    """Response model for simulation status"""
    session_id: str
    running: bool
    round_number: int
    agent_count: int
    agents: List[str]
    message: str
    phase: str  # "initializing" | "running" | "stopped"


@app.get("/api/sessions/{session_id}/status", response_model=SimulationStatusResponse)
async def get_simulation_status(session_id: str):
    """
    Get the status of a trading simulation.
    
    Phase states:
    - "initializing": Superforecasters are running, market being set up
    - "running": Trading simulation is active
    - "stopped": Simulation has stopped or completed
    """
    from app.traders.simulation import get_simulation, is_session_initializing
    from app.db.repositories import ForecasterResponseRepository
    
    simulation = get_simulation(session_id)
    
    if simulation is None:
        # Check if session exists
        session_repo = SessionRepository()
        session = session_repo.find_by_id(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # First check: is session marked as initializing in memory?
        # This catches the case immediately after /run returns but before forecaster_responses are created
        if is_session_initializing(session_id):
            return SimulationStatusResponse(
                session_id=session_id,
                running=False,
                round_number=0,
                agent_count=0,
                agents=[],
                message="Superforecasters initializing market...",
                phase="initializing",
            )
        
        # Second check: are there any running forecaster responses in DB?
        forecaster_repo = ForecasterResponseRepository()
        forecaster_responses = forecaster_repo.find_all(filters={"session_id": session_id})
        
        # Determine phase based on forecaster status
        if forecaster_responses:
            # Check if any forecaster is still running
            any_running = any(r.get("status") == "running" for r in forecaster_responses)
            if any_running:
                return SimulationStatusResponse(
                    session_id=session_id,
                    running=False,
                    round_number=0,
                    agent_count=0,
                    agents=[],
                    message="Superforecasters initializing market...",
                    phase="initializing",
                )
        
        return SimulationStatusResponse(
            session_id=session_id,
            running=False,
            round_number=0,
            agent_count=0,
            agents=[],
            message="Simulation not running (may have completed or not started)",
            phase="stopped",
        )
    
    status = simulation.get_status()
    return SimulationStatusResponse(
        session_id=session_id,
        running=status["running"],
        round_number=status["round_number"],
        agent_count=status["agent_count"],
        agents=status["agents"],
        message="Simulation is running" if status["running"] else "Simulation stopped",
        phase="running" if status["running"] else "stopped",
    )


class StopSimulationResponse(BaseModel):
    """Response model for stop simulation endpoint"""
    session_id: str
    stopped: bool
    message: str


@app.post("/api/sessions/{session_id}/stop", response_model=StopSimulationResponse)
async def stop_simulation(session_id: str):
    """
    Stop a running trading simulation.
    """
    from app.traders.simulation import get_simulation
    
    simulation = get_simulation(session_id)
    
    if simulation is None:
        # Check if session exists
        session_repo = SessionRepository()
        session = session_repo.find_by_id(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return StopSimulationResponse(
            session_id=session_id,
            stopped=False,
            message="Simulation not running (may have already stopped)",
        )
    
    if not simulation.is_running:
        return StopSimulationResponse(
            session_id=session_id,
            stopped=False,
            message="Simulation already stopped",
        )
    
    simulation.stop()
    logger.info(f"Simulation stopped for session {session_id}")
    
    return StopSimulationResponse(
        session_id=session_id,
        stopped=True,
        message="Simulation stopped.",
    )


@app.get("/api/sessions/{session_id}/orderbook")
async def get_orderbook(session_id: str):
    """
    Get the current order book for a session.
    Returns aggregated bids and asks sorted by price.
    """
    logger.info(f"GET /api/sessions/{session_id}/orderbook")
    
    from app.market import SupabaseMarketMaker
    
    market_maker = SupabaseMarketMaker()
    orderbook = market_maker.get_orderbook(session_id)
    
    return orderbook


@app.get("/api/sessions/{session_id}/trades")
async def get_trades(session_id: str, limit: int = 50):
    """
    Get recent trades for a session.
    """
    logger.info(f"GET /api/sessions/{session_id}/trades (limit={limit})")
    
    from app.market import SupabaseMarketMaker
    
    market_maker = SupabaseMarketMaker()
    trades = market_maker.get_recent_trades(session_id, limit=limit)
    
    return {"trades": trades}


class SaveSystemPromptRequest(BaseModel):
    """Request to save a trader's system prompt"""
    trader_name: str
    system_prompt: str


@app.post("/api/sessions/{session_id}/traders/{trader_name}/system_prompt")
async def save_trader_system_prompt(
    session_id: str, 
    trader_name: str,
    request: SaveSystemPromptRequest
):
    """
    Save a trader's system prompt/notes.
    Called by agents after each prediction to persist their reasoning.
    """
    logger.info(f"POST /api/sessions/{session_id}/traders/{trader_name}/system_prompt")
    
    from app.db.repositories import TraderRepository
    
    trader_repo = TraderRepository()
    result = trader_repo.save_system_prompt(
        session_id=session_id,
        trader_name=trader_name,
        system_prompt=request.system_prompt
    )
    
    if result:
        return {
            "success": True,
            "trader_name": trader_name,
            "prompt_length": len(request.system_prompt)
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Trader {trader_name} not found in session {session_id}"
        )


@app.get("/api/sessions/{session_id}/traders")
async def get_session_traders(session_id: str):
    """
    Get all traders and their states for a session.
    """
    logger.info(f"GET /api/sessions/{session_id}/traders")
    
    from app.db.repositories import TraderRepository
    
    trader_repo = TraderRepository()
    traders = trader_repo.get_session_traders(session_id)
    
    return {"traders": traders}


@app.get("/api/sessions/{session_id}/traders/{trader_name}")
async def get_trader_state(session_id: str, trader_name: str):
    """
    Get a specific trader's state including system_prompt.
    """
    logger.info(f"GET /api/sessions/{session_id}/traders/{trader_name}")
    
    from app.db.repositories import TraderRepository
    
    trader_repo = TraderRepository()
    trader = trader_repo.get_trader(session_id, trader_name)
    
    if trader:
        return trader
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Trader {trader_name} not found in session {session_id}"
        )


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
