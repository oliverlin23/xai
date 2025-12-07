"""
Logging configuration for the application

Set LOG_LEVEL environment variable to control verbosity:
- DEBUG: All messages
- INFO: Normal operation (default for development)
- WARNING: Only warnings and errors (recommended for production)
- ERROR: Only errors
"""
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Get log level from environment (default: WARNING for cleaner output)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING").upper()
_log_level = getattr(logging, LOG_LEVEL, logging.WARNING)

# Create formatter
formatter = logging.Formatter(
    fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Console handler (for general flow)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(_log_level)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(_log_level)
root_logger.addHandler(console_handler)

# Suppress noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Track agent loggers to avoid duplicate handlers
_agent_loggers = {}

def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module"""
    logger = logging.getLogger(name)
    logger.setLevel(_log_level)
    if not logger.handlers:
        logger.addHandler(console_handler)
    return logger

def get_agent_logger(session_id: str, agent_name: str) -> logging.Logger:
    """
    Get a logger for a specific agent with its own log file
    
    Args:
        session_id: Session ID
        agent_name: Agent name (e.g., 'discovery_1', 'validator')
    
    Returns:
        Logger instance with both console and file handlers
    """
    logger_key = f"{session_id}_{agent_name}"
    
    if logger_key in _agent_loggers:
        return _agent_loggers[logger_key]
    
    # Create logger
    logger = logging.getLogger(f"agent.{session_id}.{agent_name}")
    logger.setLevel(_log_level)
    logger.propagate = False  # Don't propagate to root logger
    
    # Console handler (for general flow)
    console_handler_agent = logging.StreamHandler(sys.stdout)
    console_handler_agent.setFormatter(formatter)
    console_handler_agent.setLevel(_log_level)
    logger.addHandler(console_handler_agent)
    
    # File handler (separate file per agent) - always INFO for debugging
    session_logs_dir = LOGS_DIR / session_id
    session_logs_dir.mkdir(exist_ok=True)
    
    log_file = session_logs_dir / f"{agent_name}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)  # File logs are always INFO for debugging
    logger.addHandler(file_handler)
    
    # Store for reuse
    _agent_loggers[logger_key] = logger
    
    return logger

