"""Configuration settings for the AI Analysis Service."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # App settings
    app_name: str = Field(default="Lead Finder AI Analysis Service")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # Server settings
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    # MongoDB settings
    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="leadfinder")
    
    # Backend settings
    backend_url: str = Field(default="http://localhost:5000")
    frontend_url: Optional[str] = Field(default=None)
    
    # Analysis settings
    analysis_timeout: int = Field(default=30)
    bulk_analysis_concurrency: int = Field(default=5)
    
    # Logging settings
    log_level: str = Field(default="INFO")
    
    # X11 Display settings for cloud environments
    disable_x11_features: bool = Field(default=False)
    
    @property
    def is_production(self) -> bool:
        return not self.debug


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
