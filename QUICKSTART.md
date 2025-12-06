# Quick Start Guide

## Prerequisites

1. **Install uv** (Python package manager)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or: brew install uv
   ```

2. **Install Node.js 18+**
   ```bash
   # Check: node --version
   ```

3. **Get API Keys**
   - Grok API key from xAI
   - Supabase project at https://supabase.com

## Setup (5 minutes)

### 1. Backend Setup

```bash
cd backend

# Install all dependencies from pyproject.toml
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your GROK_API_KEY and SUPABASE credentials

# Run server
uv run uvicorn app.main:app --reload --port 8000
```

### 2. Database Setup

1. Go to your Supabase project
2. Open SQL Editor
3. Copy and run `backend/supabase/migrations/001_create_tables.sql`
4. Verify tables were created in Table Editor

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment
cp .env.local.example .env.local
# Edit .env.local with your NEXT_PUBLIC_SUPABASE_* credentials

# Run dev server
npm run dev
```

## Verify Setup

1. Backend: http://localhost:8000/health should return `{"status":"healthy"}`
2. Frontend: http://localhost:3000 should show the homepage

## Common uv Commands

```bash
# Sync dependencies (like npm install)
uv sync

# Add a new package
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Run a command in the virtual environment
uv run python script.py
uv run uvicorn app.main:app

# Show installed packages
uv pip list
```

## Next Steps

1. Enter a forecasting question on the homepage
2. Watch the 24 agents work in real-time
3. View the final prediction with confidence score

For detailed documentation, see [README.md](README.md)
