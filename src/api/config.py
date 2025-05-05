from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Settings:
    environment: str = "local"
    enable_cors: bool = True
    cors_origins: list = field(default_factory=list)
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # GitHub App settings
    github_app_id: str = ""
    github_private_key_path: str = ""
    github_webhook_secret: str = ""
    github_api_url: str = "https://api.github.com"
    # OpenRouter settings
    open_router_api_key: str = ""
    open_router_base_url: str = "https://openrouter.ai/api/v1"
    model_name: str = "google/gemini-2.0-flash-001"

    @property
    def github_private_key(self) -> str:
        with open(self.github_private_key_path, "r") as f:
            return f.read()

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings, cached for performance.
    """
    return Settings(
        environment="local",
        github_app_id=os.getenv("GITHUB_APP_ID", ""),
        github_private_key_path=os.getenv("GITHUB_PRIVATE_KEY_PATH", ""),
        github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
        open_router_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        open_router_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model_name=os.getenv("MODEL_NAME", "google/gemini-2.0-flash-001"),
    )