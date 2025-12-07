"""
Verify actual Supabase database schema matches our models.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Tables we want to verify
TABLES = [
    "sessions",
    "forecaster_responses", 
    "agent_logs",
    "factors",
    "trader_state_live",
    "trader_prompts_history",
    "orderbook_live",
    "orderbook_history",
    "trades"
]

def get_table_columns(table_name: str):
    """Query information_schema for table columns"""
    # Use raw SQL via RPC or just select from the table with limit 0
    # Actually, easier approach - just do a select and look at the response structure
    try:
        result = supabase.table(table_name).select("*").limit(1).execute()
        if result.data:
            return list(result.data[0].keys())
        else:
            # No data - try to get column names from an empty query
            # The columns should still be in the response metadata
            print(f"  (no rows in {table_name})")
            return []
    except Exception as e:
        return f"ERROR: {e}"

def main():
    print("=" * 60)
    print("ACTUAL SUPABASE DATABASE SCHEMA")
    print("=" * 60)
    
    for table in TABLES:
        print(f"\n📋 {table}")
        print("-" * 40)
        columns = get_table_columns(table)
        if isinstance(columns, str):  # Error
            print(f"  {columns}")
        elif columns:
            for col in sorted(columns):
                print(f"  • {col}")
        else:
            print("  (empty table - columns unknown)")
    
    print("\n" + "=" * 60)
    print("To see column TYPES, run this SQL in Supabase SQL Editor:")
    print("=" * 60)
    print("""
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN (
    'sessions', 'forecaster_responses', 'agent_logs', 
    'factors', 'trader_state_live', 'trader_prompts_history',
    'orderbook_live', 'orderbook_history', 'trades'
)
ORDER BY table_name, ordinal_position;
""")

if __name__ == "__main__":
    main()
