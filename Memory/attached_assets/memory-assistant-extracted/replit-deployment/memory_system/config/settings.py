"""
Configuration settings for Memory Harvester Agent
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseSettings, Field
from pathlib import Path

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_api_base: str = Field(default="https://api.openai.com/v1", env="OPENAI_API_BASE")
    
    # Database
    database_url: str = Field(default="sqlite:///data/memories.db", env="DATABASE_URL")
    
    # Security
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    
    # Processing
    max_batch_size: int = Field(default=100, env="MAX_BATCH_SIZE")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    processing_timeout: int = Field(default=30, env="PROCESSING_TIMEOUT")
    
    # Feature flags
    enable_ocr: bool = Field(default=True, env="ENABLE_OCR")
    enable_speech_recognition: bool = Field(default=True, env="ENABLE_SPEECH_RECOGNITION")
    enable_image_analysis: bool = Field(default=True, env="ENABLE_IMAGE_ANALYSIS")
    enable_web_scraping: bool = Field(default=True, env="ENABLE_WEB_SCRAPING")
    
    # Paths
    data_dir: Path = Field(default=Path("data"))
    cache_dir: Path = Field(default=Path("data/cache"))
    logs_dir: Path = Field(default=Path("data/logs"))
    
    # Replit specific
    repl_slug: Optional[str] = Field(default=None, env="REPL_SLUG")
    repl_owner: Optional[str] = Field(default=None, env="REPL_OWNER")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

