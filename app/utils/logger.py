"""Logging utilities for the AI Analysis Service."""

import logging
import sys
from typing import Optional

from loguru import logger as loguru_logger

from ..config.settings import settings

def setup_logging(level: Optional[str] = None) -> None:
    """Setup logging configuration."""
    log_level = level or settings.log_level
    
    # Remove default handlers
    loguru_logger.remove()
    
    # Add console handler
    loguru_logger.add(
        sys.stdout,
        level=log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        backtrace=True,
        diagnose=True,
    )
    
    # Add file handler for errors
    if not settings.debug:
        loguru_logger.add(
            "logs/analysis_{time:YYYY-MM-DD}.log",
            level="ERROR",
            rotation="1 day",
            retention="7 days",
            encoding="utf-8",
        )
    
    # Configure logging module
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def get_logger(name: str) -> loguru_logger:
    """Get a logger instance."""
    return loguru_logger.bind(name=name)
