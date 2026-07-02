"""Structured logger for the Python Scraper Service."""

import sys
from loguru import logger

from scraper_service.config.settings import settings


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )
    logger.add(
        "logs/scraper_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=settings.debug,
        encoding="utf-8",
    )


__all__ = ["logger", "setup_logging"]
