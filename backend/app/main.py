"""
FastAPI application entry point for Superforecaster
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

app = FastAPI(
    title="Superforecaster API",
    description="24-agent superforecasting system powered by Grok AI",
    version="0.1.0"
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ForecastRequest(BaseModel):
    question_text: str
    question_type: str = "binary"  # binary, numeric, categorical


class ForecastResponse(BaseModel):
    id: str
    question_text: str
    status: str
    created_at: datetime


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "superforecaster-api"}


@app.post("/api/forecasts", response_model=ForecastResponse)
async def create_forecast(request: ForecastRequest, background_tasks: BackgroundTasks):
    """
    Create a new forecast session and start agent workflow
    """
    session_id = str(uuid.uuid4())

    # TODO: Create session in Supabase
    # TODO: Start orchestrator in background
    # background_tasks.add_task(run_orchestrator, session_id, request.question_text)

    return ForecastResponse(
        id=session_id,
        question_text=request.question_text,
        status="running",
        created_at=datetime.now()
    )


@app.get("/api/forecasts/{forecast_id}")
async def get_forecast(forecast_id: str):
    """
    Get forecast session details including status, result, factors, and agent logs
    """
    # TODO: Fetch from Supabase
    raise HTTPException(status_code=404, detail="Forecast not found")


@app.get("/api/forecasts")
async def list_forecasts(limit: int = 10, offset: int = 0):
    """
    List all past forecast sessions
    """
    # TODO: Fetch from Supabase
    return {"forecasts": [], "total": 0}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
