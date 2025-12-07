# Superforecaster Application - Implementation Plan

## Overview
Build a single-user superforecasting application with 24 collaborative AI agents powered by Grok API. The system takes a forecasting question, orchestrates agents through 4 phases (factor discovery, validation, research, synthesis), and produces a prediction with confidence scores.

## Technology Stack

### Backend
- **FastAPI** (Python 3.11+) - Async API with type hints and auto-docs
- **uv** - Ultra-fast Python package manager (replaces pip/poetry)
- **Supabase** - Managed PostgreSQL database with Realtime subscriptions
- **xAI SDK** - Grok API integration with streaming
- **SQLAlchemy 2.0** - Async ORM with type annotations
- **Supabase Python Client** - Database access and Realtime pub/sub
- **Pydantic v2** - Data validation and structured outputs

### Frontend
- **Next.js 14 + TypeScript** - React framework with App Router
- **Tailwind CSS + shadcn/ui** - Styling and components
- **React Query (TanStack Query)** - Server state management
- **Supabase JS Client** - Database queries and Realtime subscriptions

### Development
- **Local Backend**: FastAPI server running locally
- **Supabase Cloud**: Managed database and Realtime (free tier available)

## Agent Architecture

### 24-Agent System (4 Phases)

**Phase 1: Factor Discovery** (10 agents, all parallel)
- Agent 1-10: Factor Discovery Specialists
- Each agent independently discovers up to 5 relevant factors
- Diversity encouraged: economic, social, political, technical, environmental, etc.
- Total output: Up to 50 factors (redundancy is good for validation)

**Phase 2: Factor Validation** (3 agents, sequential)
- Agent 11: Factor Validator - Deduplicates and validates all factors from Phase 1
- Agent 12: Importance Rater - Scores each unique factor 1-10 for importance
- Agent 13: Consensus Builder - Selects top 5 factors for deep research

**Phase 3: Research** (10 agents, parallel)
- Agent 14-18: Historical Pattern Analysts (5 agents)
  - Each agent analyzes historical precedents for one of the top 5 factors
  - One agent per factor for deep historical analysis
- Agent 19-23: Current Data Researchers (5 agents)
  - Each agent researches current data/trends for one of the top 5 factors
  - One agent per factor for current information gathering
- All 10 agents run in parallel for speed

**Phase 4: Synthesis** (1 agent)
- Agent 24: Prediction Synthesizer
  - Combines all research from Phase 3
  - Generates final prediction with reasoning
  - Calculates confidence score

## Database Schema (Simplified for Hackathon)

```sql
-- Core table: Everything about a forecast session
sessions
- id (UUID, PK)
- question_text (TEXT) -- The forecasting question
- question_type (VARCHAR) -- binary, numeric, categorical
- status (VARCHAR) -- running, completed, failed
- current_phase (VARCHAR) -- factor_discovery, validation, research, synthesis
- created_at (TIMESTAMP)
- started_at (TIMESTAMP)
- completed_at (TIMESTAMP)
- prediction_result (JSONB) -- Final prediction with confidence, reasoning, factors
  -- Structure: {prediction: string, confidence: number, reasoning: string, key_factors: [...]}
- total_cost_tokens (INTEGER) -- Sum of all agent tokens for this session
- INDEX idx_status (status)
- INDEX idx_created_at (created_at DESC)

-- Agent execution logs (for real-time updates and debugging)
agent_logs
- id (UUID, PK)
- session_id (FK → sessions.id)
- agent_name (VARCHAR) -- e.g., "discovery_1", "validator", "historical_3"
- phase (VARCHAR) -- factor_discovery, validation, research, synthesis
- status (VARCHAR) -- running, completed, failed
- output_data (JSONB) -- Structured agent output (validated via Pydantic)
- error_message (TEXT)
- tokens_used (INTEGER) -- Total tokens for this agent run
- created_at (TIMESTAMP)
- completed_at (TIMESTAMP)
- INDEX idx_session_logs (session_id, created_at DESC)
- INDEX idx_phase (phase)

-- Discovered factors (for UI visualization)
factors
- id (UUID, PK)
- session_id (FK → sessions.id)
- name (VARCHAR)
- description (TEXT)
- category (VARCHAR) -- economic, social, technical, etc.
- importance_score (DECIMAL) -- 0.00 to 10.00
- research_summary (TEXT) -- Combined research from Phase 3
- created_at (TIMESTAMP)
- INDEX idx_session_factors (session_id)
- INDEX idx_importance (session_id, importance_score DESC)
```

**Simplifications for Hackathon**:
- **3 tables instead of 6**: Merged related data (questions+sessions, research into factors, predictions into sessions)
- **Denormalized data**: `prediction_result` JSONB stores everything in one place for fast retrieval
- **Minimal tracking**: Removed retry_count, timeout_seconds, separate token columns (just `tokens_used` total)
- **No separate questions table**: Question text lives directly in sessions (single-user app)
- **Research merged into factors**: `research_summary` instead of separate `factor_research` table
- **Faster queries**: Fewer JOINs needed for UI

## API Endpoints

### REST Endpoints (Simplified)
```
GET    /health                          # Health check endpoint
POST   /api/forecasts                   # Create new forecast session + start agents
GET    /api/forecasts/{id}              # Get session (includes status, result, factors)
GET    /api/forecasts                   # List all past forecasts
```

**Simplified for Hackathon**:
- Removed separate endpoints for `/status`, `/result`, `/agents`, `/factors`, `/costs`
- Single `GET /api/forecasts/{id}` returns everything:
  ```json
  {
    "id": "...",
    "question_text": "Will Bitcoin reach $150k by 2025?",
    "status": "completed",
    "current_phase": "synthesis",
    "prediction_result": {
      "prediction": "65% probability Bitcoin reaches $150k by Dec 2025",
      "confidence": 0.72,
      "reasoning": "...",
      "key_factors": [...]
    },
    "factors": [...],  // All factors with research
    "agent_logs": [...],  // Recent agent activity
    "total_cost_tokens": 45230,
    "created_at": "...",
    "completed_at": "..."
  }
  ```
- Frontend gets everything in one request = faster, simpler

### Supabase Realtime (Simplified)
Frontend subscribes to Supabase Realtime channels for live updates:
- **Table: `agent_logs`** - Subscribe to inserts for session_id (agent starts/completes)
- **Table: `factors`** - Subscribe to inserts for session_id (factors discovered)
- **Table: `sessions`** - Subscribe to updates for session_id (status changes, final result)

**Example subscription** (Next.js):
```typescript
const channel = supabase
  .channel(`session:${sessionId}`)
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'agent_logs',
    filter: `session_id=eq.${sessionId}`
  }, (payload) => {
    // Update UI with new agent activity
  })
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'sessions',
    filter: `id=eq.${sessionId}`
  }, (payload) => {
    // Update status/phase or show final result
  })
  .subscribe()
```

No custom WebSocket server needed - Supabase Realtime handles all pub/sub!

## Project Structure

```
xai/
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app entry point with all routes
│   │   ├── models.py                    # SQLAlchemy models (sessions, agent_logs, factors)
│   │   ├── schemas.py                   # Pydantic request/response models
│   │   ├── agents/
│   │   │   ├── base.py                  # BaseAgent class (CRITICAL)
│   │   │   ├── orchestrator.py          # Workflow coordinator (CRITICAL)
│   │   │   ├── discovery.py             # Discovery agents (1-10)
│   │   │   ├── validation.py            # Validation agents (11-13)
│   │   │   ├── research.py              # Research agents (14-23)
│   │   │   ├── synthesis.py             # Synthesis agent (24)
│   │   │   └── prompts.py               # All agent system prompts
│   │   ├── services/
│   │   │   └── grok.py                  # Grok API wrapper (CRITICAL)
│   │   └── core/
│   │       ├── supabase.py              # Supabase client connection
│   │       └── config.py                # Environment config
│   ├── supabase/
│   │   └── migrations/
│   │       └── 001_create_tables.sql    # 3-table schema
│   ├── pyproject.toml                   # uv dependencies
│   └── .env
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                   # Root layout
│   │   ├── page.tsx                     # Home page (question input)
│   │   ├── forecast/
│   │   │   └── [id]/
│   │   │       ├── page.tsx             # Monitor page (real-time updates)
│   │   │       └── result/
│   │   │           └── page.tsx         # Result page (final prediction)
│   │   ├── history/
│   │   │   └── page.tsx                 # History page (past forecasts)
│   │   └── api/                         # API routes (optional)
│   ├── components/
│   │   ├── forecast/
│   │   │   ├── QuestionInput.tsx        # Question submission form
│   │   │   ├── ForecastCard.tsx         # Display prediction results
│   │   │   └── ConfidenceGauge.tsx      # Confidence visualization
│   │   ├── agents/
│   │   │   ├── AgentMonitor.tsx         # Real-time agent activity
│   │   │   ├── AgentTimeline.tsx        # Phase progression visual
│   │   │   └── AgentCard.tsx            # Individual agent status
│   │   └── factors/
│   │       ├── FactorList.tsx           # Display factors
│   │       └── FactorImportance.tsx     # Importance scores visual
│   ├── hooks/
│   │   ├── useForecast.ts               # Forecast API hook
│   │   └── useRealtimeAgents.ts         # Supabase Realtime subscription
│   ├── lib/
│   │   ├── api.ts                       # API client (fetch wrapper)
│   │   └── supabase.ts                  # Supabase client initialization
│   ├── types/
│   │   ├── forecast.ts                  # TypeScript types
│   │   └── agent.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── .env.local
│
└── .envexample
```

**Project Structure Simplifications for Hackathon**:
- **Flat API structure**: All routes in `main.py` instead of nested `api/v1/routes/`
- **Single models file**: `models.py` instead of separate `database.py` + `forecast.py`
- **Single schemas file**: `schemas.py` for all Pydantic models
- **Agent files by phase**: One file per phase instead of separate files per agent type
- **Minimal services**: Just `grok.py` (removed forecast_service, websocket_manager)
- **Fewer files overall**: ~15 Python files instead of 25+

## Implementation Phases

### Phase 1: Foundation (Priority 1)
**Goal**: Set up infrastructure and database

1. **Project Setup**
   - Create `backend/` and `frontend/` directories
   - Initialize FastAPI project with `uv` (modern Python package manager)
   - Initialize Next.js 14 + TypeScript with App Router via `create-next-app`
   - Set up Supabase project (free tier) at supabase.com

2. **Supabase Database Setup**
   - Create Supabase project and get connection credentials
   - Write SQL migration in `backend/supabase/migrations/001_create_tables.sql`
   - Create 3 tables: `sessions`, `agent_logs`, `factors`
   - Enable Realtime on all tables via Supabase dashboard
   - Implement SQLAlchemy models in `backend/app/models/forecast.py` matching schema

3. **Basic API Structure**
   - Create FastAPI app in `backend/app/main.py`
   - Configure Supabase client in `backend/app/core/supabase.py`
   - Implement basic endpoints in `backend/app/api/routes.py` (simplified structure)
   - Set up CORS for local frontend (port 3000)
   - Basic error handling and logging

**Files Created** (minimal for hackathon):
- `backend/pyproject.toml` - uv dependencies (fastapi, uvicorn, supabase, pydantic, sqlalchemy)
- `backend/app/main.py` - FastAPI app entry point
- `backend/app/models.py` - SQLAlchemy models (sessions, agent_logs, factors)
- `backend/app/core/supabase.py` - Supabase client singleton
- `backend/supabase/migrations/001_create_tables.sql` - 3-table schema
- `frontend/package.json` - Next.js + shadcn/ui + Supabase client
- `frontend/app/layout.tsx` - Root layout
- `frontend/app/page.tsx` - Main page (question input)
- `frontend/lib/supabase.ts` - Supabase client

### Phase 2: Agent Framework (Priority 2)
**Goal**: Build core agent system with Grok integration

1. **Base Agent System**
   - Implement `BaseAgent` class in `backend/app/agents/base.py` (CRITICAL)
     - Grok API client initialization
     - Async streaming response handling with token tracking
     - **Structured Output Enforcement**: Each agent must define a Pydantic output schema
       - Forces Grok to return valid JSON matching the schema
       - Ensures `output_data` in database is always queryable
       - Example: All outputs have consistent keys like "factors", "confidence_score", etc.
     - Output validation framework (validates against agent-specific Pydantic schema)
     - Progress reporting via callbacks
     - Token usage tracking (prompt_tokens, completion_tokens)
   - Implement Grok service wrapper in `backend/app/services/grok_service.py` (CRITICAL)
     - Async chat with streaming
     - Conversation management
     - Token usage extraction from API responses
     - Error handling and retries with exponential backoff

2. **Orchestrator**
   - Implement workflow engine in `backend/app/agents/orchestrator.py` (CRITICAL)
     - Phase state machine
     - Agent spawning (parallel/sequential using asyncio)
     - Progress tracking and database logging via Supabase
     - Database inserts/updates trigger Supabase Realtime automatically (no manual broadcasting)
     - Error recovery with retry logic

3. **Agent Prompts & Output Schemas**
   - Create system prompts for all agent types in `backend/app/agents/prompts/agent_prompts.py`
   - Define Pydantic output schemas for each agent type:
     - **Phase 1 (Discovery)**: `FactorDiscoveryOutput` - list of factors with name, description, category
     - **Phase 2 (Validation)**:
       - `FactorValidationOutput` - deduplicated factors
       - `FactorRatingOutput` - factors with importance scores
       - `ConsensusOutput` - top 5 factors selected
     - **Phase 3 (Research)**:
       - `HistoricalResearchOutput` - historical analysis with sources, confidence
       - `CurrentDataOutput` - current data findings with sources, confidence
     - **Phase 4 (Synthesis)**: `PredictionOutput` - prediction text, value, reasoning, confidence_score, key_factors
   - All schemas enforced via Grok API structured output mode

**Files Created**:
- `backend/app/agents/base.py` (CRITICAL)
- `backend/app/agents/orchestrator.py` (CRITICAL)
- `backend/app/services/grok_service.py` (CRITICAL)
- `backend/app/agents/prompts/agent_prompts.py`

### Phase 3: Discovery & Validation Agents (Priority 3)
**Goal**: Implement agents for Phase 1 (discovery) and Phase 2 (validation)

1. **Phase 1 Agents**
   - `backend/app/agents/phase1_discovery/discovery_agent.py` (Agents 1-10)
     - Single implementation class, orchestrator spawns 10 instances
     - Each instance independently discovers up to 5 factors
     - Inherits from BaseAgent, uses discovery system prompt
     - Output: JSON list of factors with name, description, category, relevance

2. **Phase 2 Agents**
   - `backend/app/agents/phase2_validation/validator_agent.py` (Agent 11)
     - Takes all factors from Agents 1-10, deduplicates, validates
   - `backend/app/agents/phase2_validation/rater_agent.py` (Agent 12)
     - Rates each validated factor 1-10 for importance
   - `backend/app/agents/phase2_validation/consensus_agent.py` (Agent 13)
     - Selects top 5 factors for deep research

3. **Testing**
   - Test Phase 1 + Phase 2 workflow with sample questions
   - Verify 10 agents discover factors (up to 50 total)
   - Verify validation narrows to top 5 factors

**Files Created**:
- 4 agent implementation files (Phase 1 & 2)

### Phase 4: Research & Synthesis Agents (Priority 4)
**Goal**: Implement agents for Phase 3 (research) and Phase 4 (synthesis)

1. **Phase 3 Agents**
   - `backend/app/agents/phase3_research/historical_agent.py` (Agents 14-18)
     - Single implementation class, orchestrator spawns 5 instances
     - Each instance analyzes historical patterns for one of the top 5 factors
     - One factor per agent for deep analysis
   - `backend/app/agents/phase3_research/current_data_agent.py` (Agents 19-23)
     - Single implementation class, orchestrator spawns 5 instances
     - Each instance researches current data/trends for one of the top 5 factors
     - Uses web search and available APIs for current information
     - One factor per agent for deep research

2. **Phase 4 Agents**
   - `backend/app/agents/phase4_synthesis/synthesizer_agent.py` (Agent 24)
     - Combines all research from Phase 3 (10 agent outputs)
     - Generates final prediction with reasoning
     - Calculates confidence score and uncertainty ranges

3. **Data Sources Integration**
   - Grok API used for all agent reasoning
   - Optional: Web search APIs for current data (Agent 19-23)
   - Optional: External data APIs as needed

**Files Created**:
- 3 agent implementation files (Phase 3 & 4)

### Phase 5: API & Realtime Integration (Priority 5)
**Goal**: Complete backend API with Supabase Realtime

1. **Forecast Endpoints**
   - Implement `POST /api/v1/forecast/create` in `backend/app/api/v1/routes/forecast.py`
     - Create forecast_session in Supabase
     - Start orchestrator asynchronously (background task)
     - Return session_id for client to subscribe to Realtime updates
   - Implement `GET /api/v1/forecast/{id}/status`
   - Implement `GET /api/v1/forecast/{id}/result`
   - Implement `GET /api/v1/forecast/{id}/agents`
   - Implement `GET /api/v1/forecast/{id}/factors`
   - Implement `GET /api/v1/forecast/{id}/costs`
   - Implement `GET /api/v1/forecasts` (list all past forecasts)

2. **Supabase Integration**
   - Configure Supabase client with service role key for backend
   - Implement database insert/update helpers
   - Ensure all agent_executions, factors, predictions are written to Supabase
   - Supabase Realtime automatically broadcasts changes to subscribed clients

3. **Background Task Management**
   - Use FastAPI BackgroundTasks for async orchestrator execution
   - Ensure proper error handling and status updates
   - Log all agent executions to Supabase database

**Files Created**:
- `backend/app/api/v1/routes/forecast.py` (CRITICAL)
- `backend/app/api/v1/schemas/forecast.py`

### Phase 6: Frontend UI (Priority 6)
**Goal**: Build Next.js UI with real-time monitoring

1. **Pages (App Router)**
   - `app/page.tsx` - Home page with question input form
     - Input: question text, question type, resolution criteria, target date
     - Submit to `POST /api/v1/forecast/create`
     - Redirect to monitor page on submission
   - `app/forecast/[id]/page.tsx` - Monitor page
     - Real-time agent monitoring during execution
     - Shows current phase, active agents, completed agents
     - Auto-navigates to result page when complete
   - `app/forecast/[id]/result/page.tsx` - Result page
     - Final prediction display with confidence score
     - Factor importance visualization
     - Reasoning explanation
   - `app/history/page.tsx` - History page
     - List of past forecasts
     - Click to view results
   - `app/layout.tsx` - Root layout with navigation

2. **Core Components**
   - `components/forecast/QuestionInput.tsx` - Question submission form
   - `components/agents/AgentMonitor.tsx` - Real-time agent activity display
   - `components/agents/AgentTimeline.tsx` - Visual phase progression (Phase 1 → 2 → 3 → 4)
   - `components/agents/AgentCard.tsx` - Individual agent status card
   - `components/factors/FactorList.tsx` - Display discovered factors with importance scores
   - `components/factors/FactorImportance.tsx` - Bar chart or visualization of factor importance
   - `components/forecast/ForecastCard.tsx` - Final prediction display
   - `components/forecast/ConfidenceGauge.tsx` - Visual confidence score (0-100%)

3. **Hooks & Services**
   - `hooks/useRealtimeAgents.ts` - Supabase Realtime subscription hook
     - Subscribes to agent_executions table for session_id
     - Returns real-time agent updates, loading state
     - Auto-cleanup on unmount
   - `hooks/useForecast.ts` - React Query hook for forecast API
   - `lib/api.ts` - API client with fetch wrapper
   - `lib/supabase.ts` - Supabase client initialization (anon key for frontend)

**Files Created**:
- 5 page components (Next.js App Router)
- 8+ reusable components
- 2 custom hooks
- 2 lib files
- TypeScript type definitions

### Phase 7: Integration & Testing (Priority 7)
**Goal**: End-to-end testing and refinement

1. **Integration Testing**
   - Test full workflow: question → 24 agents → prediction
   - Verify Supabase database persistence
   - Test Supabase Realtime updates in frontend
   - Error handling (agent failures, API limits, timeouts)

2. **UI/UX Polish**
   - Responsive design (desktop focus for MVP)
   - Loading states and skeletons
   - Error messages and retry buttons
   - Smooth phase transitions

3. **Performance**
   - Optimize agent parallel execution
   - Cache Grok responses where possible
   - Database query optimization

## Critical Files (Build in This Order)

1. **backend/supabase/migrations/001_create_tables.sql**
   3-table schema (sessions, agent_logs, factors) - create in Supabase first

2. **backend/app/models.py**
   SQLAlchemy models matching Supabase schema

3. **backend/app/core/supabase.py**
   Supabase client singleton for database operations

4. **backend/app/services/grok.py**
   Grok API wrapper with async streaming, token tracking

5. **backend/app/agents/base.py**
   BaseAgent class with Pydantic output validation

6. **backend/app/agents/orchestrator.py**
   Workflow engine coordinating all 24 agents through 4 phases

7. **backend/app/main.py**
   FastAPI app with 3 endpoints (POST/GET forecasts)

## Environment Variables (Minimal)

Create `backend/.env`:
```bash
GROK_API_KEY=your-grok-api-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

Create `frontend/.env.local`:
```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Simplified for Hackathon**:
- Removed `ENVIRONMENT`, `LOG_LEVEL`, `CORS_ORIGINS` - hardcode in code
- Removed agent config (`AGENT_TIMEOUT_SECONDS`, etc.) - use constants in code
- Only essential variables remain (API keys, URLs)

## Local Development Setup

### Prerequisites
1. **Install uv** (modern Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Node.js 18+** (for Next.js)

3. **Create Supabase Project**:
   - Visit https://supabase.com and create a free project
   - Copy your project URL and API keys

### Backend Setup
```bash
cd backend

# Initialize uv project (if not already done)
uv init

# Install dependencies
uv pip install fastapi uvicorn supabase-py sqlalchemy[asyncio] asyncpg python-dotenv

# Create .env file with your credentials
cp .env.example .env
# Edit .env and add your GROK_API_KEY and SUPABASE credentials

# Run Supabase migrations
# (manually in Supabase dashboard or via supabase CLI)

# Start development server with hot reload
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env.local file
cp .env.example .env.local
# Edit .env.local and add your NEXT_PUBLIC_SUPABASE_* credentials

# Start Next.js development server
npm run dev
```

### Running Both Services
Open two terminal windows:
- Terminal 1: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
- Terminal 2: `cd frontend && npm run dev`

Access the app at http://localhost:3000

## Key Design Decisions

1. **Single-User**: No authentication system needed; simplifies architecture
2. **Supabase Backend**: Managed PostgreSQL with built-in Realtime; no Docker/Redis needed
3. **Modern Python Tooling**: uv for fast package management instead of pip
4. **Persistent Storage**: All forecasts saved to Supabase PostgreSQL for historical review
5. **Real-Time Updates**: Supabase Realtime subscriptions replace custom WebSocket server
   - Frontend subscribes to table changes (agent_executions, factors, predictions)
   - Zero backend code needed for pub/sub - Supabase handles it automatically
6. **Factor Redundancy**: 10 discovery agents (Phase 1) generate diverse factors; validation narrows to top 5
7. **Factor Visualization**: UI shows factors with importance scores, research findings
8. **Agent Phases**: 4-phase sequential workflow (discovery → validation → research → synthesis)
9. **Parallel Execution Within Phases**: Agents run in parallel within each phase (10 in Phase 1, 10 in Phase 3)
10. **Deep Research**: Phase 3 dedicates 2 agents per factor (historical + current data)
11. **Streaming Responses**: Grok API streaming for real-time progress updates
12. **Modular Agents**: Reusable agent classes instantiated multiple times by orchestrator
13. **Error Handling**: Automatic retries (max 3) with exponential backoff; agent failures logged to database
14. **Timeouts**: 300 second default timeout per agent; configurable via environment variables
15. **Cost Tracking**: Track prompt_tokens and completion_tokens per agent execution for cost analysis
    - Phase 3 (Research) expected to be ~10x more expensive than Phase 1 (Discovery)
    - Enables per-phase and per-session cost reporting
16. **Structured Output**: All agents return validated JSON via Pydantic schemas; ensures queryable database records
17. **Local Development**: No Docker required - just uv + npm; Supabase handles infrastructure

## Success Criteria

The skeleton is complete when:
- User can input a forecasting question via web UI
- Backend spawns 24 agents across 4 phases (10 → 3 → 10 → 1)
- Phase 1: 10 agents discover up to 50 factors total
- Phase 2: 3 agents validate and narrow to top 5 factors
- Phase 3: 10 agents research the 5 factors (5 historical + 5 current)
- Phase 4: 1 agent synthesizes prediction with confidence score
- Real-time progress updates visible in frontend via Supabase Realtime
- Final prediction displayed with confidence score, reasoning, and key factors
- All forecasts saved to Supabase database and accessible via history page
- Factor importance visualized in UI

## Next Steps After Skeleton

Once skeleton is complete:
1. **Prompt Engineering**: Refine agent prompts for better factor discovery and validation
2. **Confidence Calibration**: Improve confidence calculation algorithms
3. **Additional Data Sources**: Integrate news APIs, financial data, web search APIs
4. **Learning System**: Track prediction accuracy over time using Supabase functions
5. **Advanced Visualizations**: Interactive factor graphs with Recharts/D3.js
6. **Export Features**: PDF reports via React-PDF, shareable links
7. **Performance Optimization**:
   - Implement Supabase Edge Functions for lightweight operations
   - Use Supabase Storage for large data caching
   - Add Redis (Upstash) for rate limiting if needed
8. **Testing**: Pytest for backend, Vitest for frontend, Playwright for E2E
9. **Production Deployment**: Deploy FastAPI to Railway/Fly.io, frontend to Vercel
