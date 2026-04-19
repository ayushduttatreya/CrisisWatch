"""Centralized logging configuration for CrisisWatch."""

import logging
import sys
from datetime import datetime


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup a logger with consistent formatting.
    
    Format: [time] [level] [module] message
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Formatter: [time] [level] [module] message
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


# Root logger for the application
root_logger = setup_logger("crisiswatch")


def get_logger(name: str) -> logging.Logger:
    """Get a child logger with the specified name."""
    return setup_logger(f"crisiswatch.{name}")
