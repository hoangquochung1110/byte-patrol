from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import os
from pydantic import Field


class Settings(BaseSettings):
    # App settings
    app_name: str = "byte-patrol"
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS settings
    enable_cors: bool = True
    cors_origins: List[str] = ["*"]
    
    # GitHub App settings
    github_app_id: str = Field(..., env='GITHUB_APP_ID')
    github_private_key_path: str = Field(..., env='GITHUB_PRIVATE_KEY_PATH')
    github_webhook_secret: str = Field(..., env='GITHUB_WEBHOOK_SECRET')
    github_api_url: str = "https://api.github.com"
    
    @property
    def github_private_key(self) -> str:
        with open(self.github_private_key_path, "r") as f:
            return f.read()

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings, cached for performance.
    Override with environment variables if needed.
    """
    return Settings()