# Database Utilities

This folder contains all database-related utilities and helpers for working with Supabase.

## Structure

- `client.py` - Database client singleton
- `queries.py` - Query builder for common operations
- `repositories.py` - Repository classes for each table
- `utils.py` - Helper utility functions

## Usage Examples

### Using Repositories (Recommended)

```python
from app.db import SessionRepository, AgentLogRepository, FactorRepository

# Create a session
session_repo = SessionRepository()
session = session_repo.create_session(
    question_text="Will Bitcoin reach $150k by 2025?",
    question_type="binary"
)

# Create an agent log
log_repo = AgentLogRepository()
log = log_repo.create_log(
    session_id=session["id"],
    agent_name="discovery_1",
    phase="factor_discovery"
)

# Update log when agent completes
log_repo.update_log(
    log_id=log["id"],
    status="completed",
    output_data={"factors": [...]},
    tokens_used=1500
)

# Create a factor
factor_repo = FactorRepository()
factor = factor_repo.create_factor(
    session_id=session["id"],
    name="Bitcoin adoption rate",
    description="Rate of institutional adoption",
    category="economic",
    importance_score=8.5
)

# Get all factors for a session
factors = factor_repo.get_session_factors(session["id"])
```

### Using Query Builder Directly

```python
from app.db import get_db_client, QueryBuilder

client = get_db_client()
query = QueryBuilder(client, "sessions")

# Find by ID
session = query.find_by_id("some-uuid")

# Find all with filters
sessions = query.find_all(
    filters={"status": "completed"},
    order_by="created_at",
    order_desc=True,
    limit=10
)

# Create record
new_session = query.create({
    "question_text": "Test question",
    "question_type": "binary"
})

# Update record
query.update(session_id, {"status": "completed"})

# Count records
count = query.count({"status": "running"})
```

### Using Utilities

```python
from app.db.utils import generate_uuid, now_iso, prepare_data

# Generate UUID
id = generate_uuid()

# Get current timestamp
timestamp = now_iso()

# Prepare data for insertion
data = prepare_data({
    "question_text": "Test",
    "question_type": "binary"
})
```

## Available Repositories

- **SessionRepository**: Manage forecast sessions
  - `create_session()` - Create new session
  - `update_status()` - Update session status/phase/prediction
  - `add_tokens()` - Add tokens to session total

- **AgentLogRepository**: Manage agent execution logs
  - `create_log()` - Create new log entry
  - `update_log()` - Update log with results
  - `get_session_logs()` - Get all logs for a session

- **FactorRepository**: Manage discovered factors
  - `create_factor()` - Create new factor
  - `update_factor()` - Update factor with research/score
  - `get_session_factors()` - Get all factors for a session

## Migration from Old Code

Old code using `get_supabase_client()` will still work (backward compatible), but new code should use:

```python
from app.db import get_db_client  # Instead of app.core.supabase
```

