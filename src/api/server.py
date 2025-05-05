import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import Settings, get_settings
from api.middleware.logging import RequestLoggingMiddleware
from api.routes import webhooks

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("byte-patrol")

# Lifespan context manager for startup/shutdown tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections, load models, etc.
    logger.info("Starting Byte Patrol API server")
    settings = get_settings()
    logger.info(f"Environment: {settings.environment}")
    
    yield
    
    # Shutdown: Close connections, cleanup resources
    logger.info("Shutting down Byte Patrol API server")

# Create FastAPI app
def create_app() -> FastAPI:
    settings = get_settings()
    
    app = FastAPI(
        title="Byte Patrol API",
        description="GitHub App webhook server for AI-powered code reviews",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # Middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # CORS configuration
    if settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Register routes
    app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "api.server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
