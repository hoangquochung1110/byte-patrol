from fastapi import Request
import time
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
import json
from contextlib import contextmanager
from typing import Optional, Dict, Any

# Set up logger
logger = logging.getLogger("byte-patrol.middleware.logging")

# Create a context var for request ID
request_id_var = {}

@contextmanager
def request_context(request_id: str):
    """Context manager to track request ID in logs"""
    old_request_id = request_id_var.get("id")
    request_id_var["id"] = request_id
    try:
        yield
    finally:
        if old_request_id:
            request_id_var["id"] = old_request_id
        else:
            request_id_var.pop("id", None)

def get_current_request_id() -> Optional[str]:
    """Get the current request ID from context"""
    return request_id_var.get("id")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request and response logging.
    
    Features:
    - Assigns a unique ID to each request for traceability
    - Logs request details: method, path, client IP, headers
    - Logs response status, time taken
    - Can optionally log request/response bodies (configured via settings)
    - Handles errors gracefully
    """
    
    def __init__(
        self, 
        app,
        log_request_body=False,
        log_response_body=False,
        exclude_paths=None,
        max_body_length=1000
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or ["/health"]
        self.max_body_length = max_body_length
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Start timer
        start_time = time.time()
        
        # Extract request details
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_string = request.url.query
        
        # Skip logging for excluded paths
        should_log = not any(path.startswith(excluded) for excluded in self.exclude_paths)
        
        if should_log:
            # Log basic request info
            log_data = {
                "request_id": request_id,
                "client_ip": client_ip,
                "method": method,
                "path": path,
                "query": query_string or None,
                "user_agent": request.headers.get("user-agent", "unknown")
            }
            
            # Optionally log request body for non-GET requests
            if self.log_request_body and method != "GET":
                try:
                    body = await request.body()
                    # Reset the request body since we've consumed it
                    request._body = body
                    
                    # Try to parse as JSON
                    try:
                        body_str = body.decode("utf-8")
                        if len(body_str) > self.max_body_length:
                            body_str = f"{body_str[:self.max_body_length]}... [truncated]"
                        log_data["request_body"] = body_str
                    except:
                        log_data["request_body"] = "[binary data]"
                except:
                    log_data["request_body"] = "[error reading body]"
            
            logger.info(f"Request started: {json.dumps(log_data)}")
        
        # Execute the request in the context of the request ID
        with request_context(request_id):
            try:
                # Process the request
                response = await call_next(request)
                
                # Calculate process time
                process_time = time.time() - start_time
                
                if should_log:
                    # Log response info
                    response_log = {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "process_time_ms": round(process_time * 1000, 2)
                    }
                    
                    # Optionally log response body (for non-success responses)
                    if self.log_response_body and response.status_code >= 400:
                        try:
                            # This is tricky because we can't easily get the response body
                            # once it's been created. You could implement a custom response
                            # class to capture the body, but that's complex.
                            # Here we just log that we can't access it.
                            response_log["response_body"] = "[not captured]"
                        except:
                            pass
                    
                    logger.info(f"Request completed: {json.dumps(response_log)}")
                
                return response
                
            except Exception as e:
                # Log the exception
                process_time = time.time() - start_time
                
                if should_log:
                    error_log = {
                        "request_id": request_id,
                        "error": str(e),
                        "error_type": e.__class__.__name__,
                        "process_time_ms": round(process_time * 1000, 2)
                    }
                    
                    logger.error(f"Request failed: {json.dumps(error_log)}")
                
                # Re-raise the exception
                raise
