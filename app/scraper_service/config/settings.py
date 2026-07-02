"""Configuration settings for the Python Scraper Service."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service identity
    app_name: str = "Lead Finder Python Scraper Service"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    log_level: str = "INFO"

    # MongoDB (same Atlas URI as Node.js backend)
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "lead-finder"

    # Browser - ensure proper defaults and env var handling
    browser_headless: bool = True
    browser_max_pool_size: int = 3  # Ensure this is never 0 or negative
    playwright_browsers_path: str = "0"

    # Node.js backend base URL (for internal callbacks if needed)
    backend_url: str = "http://localhost:8000"

    def __post_init__(self):
        # Validate browser_max_pool_size
        if self.browser_max_pool_size <= 0:
            self.browser_max_pool_size = 3
            
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        # Ensure browser_max_pool_size is valid
        if _settings.browser_max_pool_size <= 0:
            _settings.browser_max_pool_size = 3
    return _settings


settings = get_settings()
