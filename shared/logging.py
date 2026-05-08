"""
Structured JSON logging setup for AI Batch Inference System
Enables machine-parseable logs for observability and debugging
"""

import logging
import os
import sys
from pythonjsonlogger import jsonlogger


def setup_logging(name: str, level: str = None) -> logging.Logger:
    """
    Setup structured JSON logging for a module
    
    Args:
        name: Logger name (e.g., "worker", "api")
        level: Log level (e.g., "INFO", "DEBUG"). Defaults to env var LOG_LEVEL
        
    Returns:
        Configured logger instance
    """
    if level is None:
        from .config import config
        level = config.LOG_LEVEL
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    # JSON formatter for machine parsing
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(timestamp)s %(level)s %(name)s %(message)s %(exc_info)s",
        timestamp=True
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Also add exception handler
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger
