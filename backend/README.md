# Superforecaster Backend

FastAPI backend for the 24-agent superforecasting system.

## Setup

### Prerequisites

- Python 3.11+
- uv package manager

### Installation

```bash
# Install dependencies from pyproject.toml
uv sync

# For development dependencies
uv sync --dev
```

### Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add:

```bash
GROK_API_KEY=your-grok-api-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

### Running

```bash
# Development server with auto-reload
uv run uvicorn app.main:app --reload --port 8000

# Production server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── agents/              # Agent system
│   │   ├── base.py          # BaseAgent class
│   │   ├── orchestrator.py  # Workflow coordinator
│   │   └── prompts.py       # System prompts
│   ├── services/            # External services
│   │   └── grok.py          # Grok API wrapper
│   └── core/                # Core utilities
│       ├── config.py        # Configuration
│       └── supabase.py      # Supabase client
├── supabase/
│   └── migrations/          # Database migrations
└── pyproject.toml           # Dependencies & config
```

## Development

### Adding Dependencies

```bash
# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name
```

### Code Quality

```bash
# Format code with black
uv run black .

# Lint with ruff
uv run ruff check .
```

### Testing

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/forecasts` - Create new forecast
- `GET /api/forecasts/{id}` - Get forecast details
- `GET /api/forecasts` - List all forecasts
