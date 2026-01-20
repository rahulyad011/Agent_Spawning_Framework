"""Logging configuration for runtime agents."""

import logging
import os
from typing import Optional

# Default log level from environment, can be DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with configured level."""
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
        
        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger
