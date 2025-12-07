"""
Script to run database migrations
Supports both direct PostgreSQL connection and Supabase SQL Editor instructions
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def run_migration_with_psycopg2(migration_file: str, connection_string: str = None):
    """Run migration using psycopg2"""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    
    migration_path = Path(__file__).parent.parent / "supabase" / "migrations" / migration_file
    
    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        return False
    
    logger.info(f"Reading migration file: {migration_path}")
    with open(migration_path, "r") as f:
        sql = f.read()
    
    # Get connection string from env or parameter
    if not connection_string:
        connection_string = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    
    if not connection_string:
        logger.warning("No DATABASE_URL found. Cannot execute migration automatically.")
        logger.info("")
        logger.info("To run automatically, set DATABASE_URL in .env:")
        logger.info("  DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres")
        logger.info("")
        logger.info("Or get it from Supabase Dashboard:")
        logger.info("  Settings > Database > Connection string > URI")
        logger.info("")
        return False
    
    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(connection_string)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        logger.info("Executing migration...")
        cursor.execute(sql)
        
        logger.info("✓ Migration executed successfully!")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        return False


def print_migration_instructions(migration_file: str):
    """Print migration SQL and instructions"""
    migration_path = Path(__file__).parent.parent / "supabase" / "migrations" / migration_file
    
    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        return
    
    logger.info("=" * 70)
    logger.info("MIGRATION SQL")
    logger.info("=" * 70)
    logger.info("")
    
    with open(migration_path, "r") as f:
        print(f.read())
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("INSTRUCTIONS")
    logger.info("=" * 70)
    logger.info("")
    logger.info("OPTION 1: Supabase SQL Editor (Recommended)")
    logger.info("  1. Go to: https://supabase.com/dashboard")
    logger.info("  2. Select your project")
    logger.info("  3. Go to SQL Editor (left sidebar)")
    logger.info("  4. Click 'New query'")
    logger.info("  5. Copy the SQL above and paste it")
    logger.info("  6. Click 'Run' (or press Cmd/Ctrl + Enter)")
    logger.info("")
    logger.info("OPTION 2: Command line (if you have DATABASE_URL)")
    logger.info(f"  psql $DATABASE_URL -f {migration_path}")
    logger.info("")
    logger.info("OPTION 3: Set DATABASE_URL and run this script")
    logger.info("  export DATABASE_URL='postgresql://...'")
    logger.info(f"  python scripts/run_migration.py {migration_file}")
    logger.info("")
    logger.info("=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run database migration")
    parser.add_argument(
        "migration_file",
        nargs="?",
        default="002_add_prediction_fields.sql",
        help="Migration file name (default: 002_add_prediction_fields.sql)"
    )
    parser.add_argument(
        "--connection-string",
        help="PostgreSQL connection string (or set DATABASE_URL env var)"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("Database Migration Runner")
    logger.info("=" * 70)
    logger.info("")
    
    # Try to run migration if connection string available
    connection_string = args.connection_string or os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    
    if connection_string:
        logger.info("Connection string found. Attempting to execute migration...")
        logger.info("")
        success = run_migration_with_psycopg2(args.migration_file, connection_string)
        if success:
            logger.info("")
            logger.info("Migration completed successfully!")
            sys.exit(0)
        else:
            logger.info("")
            logger.info("Automatic execution failed. See instructions below.")
            logger.info("")
    else:
        logger.info("No connection string found. Showing migration SQL and instructions...")
        logger.info("")
    
    print_migration_instructions(args.migration_file)
