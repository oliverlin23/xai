# Grok Trading Simulation

Prediction market with 18 autonomous Grok-4.1-Fast agents trading on X/Twitter sentiment.
## Setup

### Prerequisites

- Python 3.11+ with [uv](https://github.com/astral-sh/uv)
- Node.js 18+
- [Supabase](https://supabase.com) account
- [xAI/Grok API Key](https://console.x.ai/)
- [X API Key](https://console.x.com/)

### Database

Run migrations in Supabase SQL Editor (in order):

```
backend/supabase/migrations/001_create_tables.sql
backend/supabase/migrations/002_add_prediction_fields.sql
backend/supabase/migrations/003_create_trading_tables.sql
backend/supabase/migrations/004_create_forecaster_responses.sql
backend/supabase/migrations/005_create_order_matching_function.sql
```

### Backend

```bash
cd backend
uv sync
cp .env.example .env  # Add GROK_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # Add NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
npm run dev
```

## Usage

1. Visit http://localhost:3000
2. Enter a prediction question
3. Watch 18 agents trade in real-time

## Agents

| Type        | Count | Strategy                                                                 |
| ----------- | ----- | ------------------------------------------------------------------------ |
| Fundamental | 5     | Market analysis (conservative, momentum, historical, balanced, realtime) |
| Noise       | 9     | X/Twitter sphere sentiment (tech, politics, finance, academic)           |
| User        | 4     | Track specific X accounts                                                |

## License

MIT
