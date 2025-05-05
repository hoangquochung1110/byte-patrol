from fastapi import Request, HTTPException
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from api.config import get_settings

logger = logging.getLogger("byte-patrol.middleware")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get client IP and path
        client_host = request.client.host if request.client else "unknown"
        path = request.url.path
        
        # Log request
        logger.info(f"Request started: {request.method} {path} from {client_host}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate and log processing time
            process_time = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {path} "
                f"- Status: {response.status_code} - Time: {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            logger.exception(f"Request failed: {request.method} {path} - {str(e)}")
            raise
