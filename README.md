# Superforecaster - AI-Powered Forecasting System

A 24-agent superforecasting application powered by Grok API. The system takes a forecasting question, orchestrates agents through 4 phases (factor discovery, validation, research, synthesis), and produces a calibrated prediction with confidence scores.

> **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) for a 5-minute setup guide.

## Architecture

### 24-Agent System (4 Phases)

**Phase 1: Factor Discovery** (10 agents, parallel)

- 10 discovery agents independently discover up to 5 relevant factors each
- Diversity encouraged across economic, social, political, technical, environmental domains
- Total output: Up to 50 factors for validation

**Phase 2: Factor Validation** (3 agents, sequential)

- Agent 11: Factor Validator - Deduplicates and validates factors
- Agent 12: Importance Rater - Scores each factor 1-10 for importance
- Agent 13: Consensus Builder - Selects top 5 factors for deep research

**Phase 3: Research** (10 agents, parallel)

- Agents 14-18: Historical Pattern Analysts (one per top factor)
- Agents 19-23: Current Data Researchers (one per top factor)
- All run in parallel for maximum speed

**Phase 4: Synthesis** (1 agent)

- Agent 24: Prediction Synthesizer
- Combines all research, generates final prediction with confidence score

## Technology Stack

### Backend

- **FastAPI** (Python 3.11+) - Async API with type hints
- **uv** - Ultra-fast Python package manager
- **Supabase** - Managed PostgreSQL with Realtime subscriptions
- **xAI SDK** - Grok API integration
- **SQLAlchemy 2.0** - Async ORM
- **Pydantic v2** - Data validation and structured outputs

### Frontend

- **Next.js 14 + TypeScript** - React framework with App Router
- **Tailwind CSS** - Styling
- **React Query (TanStack Query)** - Server state management
- **Supabase JS Client** - Database queries and Realtime subscriptions

## Prerequisites

1. **Python 3.11+** with uv package manager
2. **Node.js 18+** and npm
3. **Supabase Account** (free tier available at https://supabase.com)
4. **Grok API Key** (from xAI)

## Quick Start

### 1. Install uv (Python package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or on macOS with Homebrew:
```bash
brew install uv
```

### 2. Set up Supabase

1. Create a free project at https://supabase.com
2. Go to Project Settings → API to get your credentials:
   - Project URL
   - Anon/Public key
   - Service role key
3. Run the database migration:
   - Go to SQL Editor in Supabase dashboard
   - Copy contents of `backend/supabase/migrations/001_create_tables.sql`
   - Execute the SQL

### 3. Backend Setup

```bash
cd backend

# Install dependencies (reads from pyproject.toml)
uv sync

# Create .env file
cp .env.example .env
# Edit .env and add your GROK_API_KEY and SUPABASE credentials

# Start development server
uv run uvicorn app.main:app --reload --port 8000
```

Backend will be running at http://localhost:8000

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local file
cp .env.local.example .env.local
# Edit .env.local and add your NEXT_PUBLIC_SUPABASE_* credentials

# Start Next.js development server
npm run dev
```

Frontend will be running at http://localhost:3000

## Environment Variables

### Backend (.env)

```bash
GROK_API_KEY=your-grok-api-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
xai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── schemas.py               # Pydantic schemas
│   │   ├── agents/
│   │   │   ├── base.py              # BaseAgent class
│   │   │   ├── orchestrator.py     # Workflow coordinator
│   │   │   └── prompts.py          # Agent system prompts
│   │   ├── services/
│   │   │   └── grok.py             # Grok API wrapper
│   │   └── core/
│   │       ├── supabase.py         # Supabase client
│   │       └── config.py           # Environment config
│   ├── supabase/
│   │   └── migrations/
│   │       └── 001_create_tables.sql
│   └── pyproject.toml
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx              # Root layout
│   │   ├── page.tsx                # Home page
│   │   ├── forecast/[id]/
│   │   │   ├── page.tsx            # Monitor page
│   │   │   └── result/
│   │   │       └── page.tsx        # Result page
│   │   └── history/
│   │       └── page.tsx            # History page
│   ├── components/
│   │   ├── forecast/               # Forecast components
│   │   ├── agents/                 # Agent monitoring
│   │   └── factors/                # Factor display
│   ├── hooks/
│   │   ├── useForecast.ts          # Forecast API hook
│   │   └── useRealtimeAgents.ts   # Realtime subscriptions
│   ├── lib/
│   │   ├── api.ts                  # API client
│   │   └── supabase.ts             # Supabase client
│   └── types/                      # TypeScript types
│
└── README.md
```

## API Endpoints

### REST Endpoints

```
GET    /health                      # Health check
POST   /api/forecasts              # Create new forecast session
GET    /api/forecasts/{id}         # Get forecast details
GET    /api/forecasts              # List all forecasts
```

### Realtime Updates

Frontend subscribes to Supabase Realtime for live updates:

- **agent_logs** - Agent execution updates
- **factors** - Discovered factors
- **sessions** - Status changes and final results

## Database Schema

### sessions

- Core forecast session data
- Question, status, current phase
- Final prediction result (JSONB)
- Total token costs

### agent_logs

- Real-time agent execution tracking
- Agent name, phase, status
- Structured output data (JSONB)
- Token usage per agent

### factors

- Discovered and validated factors
- Importance scores
- Research summaries

## Usage

1. Visit http://localhost:3000
2. Enter a forecasting question (e.g., "Will Bitcoin reach $150k by 2025?")
3. Select question type (Binary, Numeric, Categorical)
4. Click "Start Forecasting"
5. Monitor real-time agent activity on the monitor page
6. View final prediction with confidence score on the result page
7. Access past forecasts via the History page

## Development Notes

### Critical Files (Build Order)

1. `backend/supabase/migrations/001_create_tables.sql` - Database schema
2. `backend/app/models.py` - SQLAlchemy models
3. `backend/app/core/supabase.py` - Supabase client
4. `backend/app/services/grok.py` - Grok API wrapper
5. `backend/app/agents/base.py` - BaseAgent class
6. `backend/app/agents/orchestrator.py` - Workflow engine
7. `backend/app/main.py` - FastAPI app

### Next Steps

The current skeleton provides:

- Complete project structure
- Database schema with Realtime enabled
- API endpoints (stubs ready for implementation)
- Full frontend UI with real-time monitoring
- Agent framework (base classes and orchestrator)

**To complete:**

1. Implement agent execution logic in orchestrator.py
2. Create specific agent classes for each phase
3. Test end-to-end workflow
4. Add error handling and retry logic
5. Optimize agent prompts for better predictions

## License

MIT
