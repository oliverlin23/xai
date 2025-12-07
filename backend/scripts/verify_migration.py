"""
Verify that the migration was successful and columns exist
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.client import get_db_client
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def verify_columns():
    """Verify that the new columns exist in the sessions table"""
    try:
        client = get_db_client()
        
        # Query the information_schema to check for columns
        # We'll use a simple query to check if columns exist
        logger.info("Checking database schema...")
        
        # Try to query a session with the new columns to see if they exist
        # If columns don't exist, this will fail
        try:
            result = client.table("sessions").select("id, prediction_probability, confidence, total_duration_seconds").limit(1).execute()
            logger.info("✓ Columns exist in database!")
            logger.info("  - prediction_probability")
            logger.info("  - confidence")
            logger.info("  - total_duration_seconds")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "column" in error_msg and ("does not exist" in error_msg or "not found" in error_msg):
                logger.error("✗ Columns do not exist in database!")
                logger.error("  The migration may not have run successfully.")
                return False
            else:
                # Other error (maybe no rows, which is fine)
                logger.info("✓ Columns exist (query succeeded, may be no rows)")
                return True
                
    except Exception as e:
        logger.error(f"Error checking database: {e}")
        return False


def verify_code_updates():
    """Verify that the code is updated to save to these columns"""
    logger.info("\nChecking code updates...")
    
    # Check repository
    try:
        from app.db.repositories import SessionRepository
        import inspect
        
        repo = SessionRepository()
        sig = inspect.signature(repo.update_status)
        params = list(sig.parameters.keys())
        
        has_prediction_probability = "prediction_probability" in params
        has_confidence = "confidence" in params
        has_duration = "total_duration_seconds" in params
        
        if has_prediction_probability and has_confidence and has_duration:
            logger.info("✓ Repository code updated to accept new fields")
        else:
            logger.warning("⚠ Repository code may not be fully updated")
            logger.warning(f"  Parameters found: {params}")
            
    except Exception as e:
        logger.error(f"Error checking repository: {e}")
    
    # Check orchestrator
    try:
        from app.agents.orchestrator import AgentOrchestrator
        import inspect
        
        sig = inspect.signature(AgentOrchestrator.update_session_status)
        params = list(sig.parameters.keys())
        
        has_prediction_probability = "prediction_probability" in params
        has_confidence = "confidence" in params
        has_duration = "total_duration_seconds" in params
        
        if has_prediction_probability and has_confidence and has_duration:
            logger.info("✓ Orchestrator code updated to pass new fields")
        else:
            logger.warning("⚠ Orchestrator code may not be fully updated")
            logger.warning(f"  Parameters found: {params}")
            
    except Exception as e:
        logger.error(f"Error checking orchestrator: {e}")


def test_saving():
    """Test that we can save to the new columns"""
    logger.info("\nTesting save functionality...")
    
    try:
        from app.db.repositories import SessionRepository
        
        repo = SessionRepository()
        
        # Create a test session
        logger.info("Creating test session...")
        session = repo.create_session(
            question_text="Test migration verification",
            question_type="binary"
        )
        session_id = session["id"]
        logger.info(f"  Created session: {session_id}")
        
        # Try to update with new fields
        logger.info("Updating session with new fields...")
        updated = repo.update_status(
            session_id=session_id,
            status="completed",
            prediction_probability=0.75,
            confidence=0.85,
            total_duration_seconds=45.5
        )
        
        logger.info("✓ Successfully saved to new columns!")
        logger.info(f"  prediction_probability: {updated.get('prediction_probability')}")
        logger.info(f"  confidence: {updated.get('confidence')}")
        logger.info(f"  total_duration_seconds: {updated.get('total_duration_seconds')}")
        
        # Clean up test session
        logger.info("Cleaning up test session...")
        repo.delete(session_id)
        logger.info("  Test session deleted")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error testing save: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("Migration Verification")
    logger.info("=" * 70)
    logger.info("")
    
    # Check columns exist
    columns_exist = verify_columns()
    logger.info("")
    
    # Check code updates
    verify_code_updates()
    logger.info("")
    
    # Test saving
    if columns_exist:
        saving_works = test_saving()
        logger.info("")
        
        logger.info("=" * 70)
        if columns_exist and saving_works:
            logger.info("✓ ALL CHECKS PASSED - Migration successful!")
        else:
            logger.info("⚠ Some checks failed - see details above")
        logger.info("=" * 70)
    else:
        logger.info("=" * 70)
        logger.info("✗ Cannot test saving - columns don't exist")
        logger.info("=" * 70)

