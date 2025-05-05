from fastapi import Request, HTTPException, Depends
import hmac
import hashlib
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from api.config import get_settings, Settings

logger = logging.getLogger("byte-patrol.middleware.auth")

class GitHubWebhookAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to verify GitHub webhook signatures.
    
    GitHub signs webhook payloads with a secret token and includes the signature
    in the X-Hub-Signature-256 header. This middleware verifies that signature
    to ensure the webhook is legitimate.
    """
    
    def __init__(self, app, webhook_path="/webhooks/github"):
        super().__init__(app)
        self.webhook_path = webhook_path
        self.settings = get_settings()
        
    async def dispatch(self, request: Request, call_next):
        # Only verify signatures for the GitHub webhook endpoint
        if request.url.path == self.webhook_path:
            # Get the signature from the header
            signature_header = request.headers.get("X-Hub-Signature-256")
            
            if not signature_header:
                logger.warning("Missing X-Hub-Signature-256 header in GitHub webhook")
                raise HTTPException(
                    status_code=401, 
                    detail="Missing X-Hub-Signature-256 header"
                )
            
            # Get the payload body
            payload_body = await request.body()
            
            # Verify the signature
            if not self._verify_signature(payload_body, signature_header):
                logger.warning("Invalid webhook signature")
                raise HTTPException(
                    status_code=401, 
                    detail="Invalid webhook signature"
                )
                
            # Reset the request body for further processing
            # This is necessary because once we read the body, it's consumed
            request._body = payload_body
        
        # Continue processing the request
        return await call_next(request)
    
    def _verify_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """
        Verify the GitHub webhook signature.
        
        Args:
            payload_body: Raw request body bytes
            signature_header: X-Hub-Signature-256 header value
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            secret = self.settings.github_webhook_secret.encode()
            signature = "sha256=" + hmac.new(
                secret, 
                payload_body, 
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, signature_header)
        except Exception as e:
            logger.exception(f"Error verifying webhook signature: {str(e)}")
            return False


# Standalone function alternative for use as a dependency
async def verify_github_signature(
    request: Request, 
    settings: Settings = Depends(get_settings)
) -> None:
    """
    Verify GitHub webhook signature as a dependency.
    
    This can be used as a dependency in route functions instead of as middleware
    when you only need to secure specific endpoints.
    
    Example:
        @router.post("/github", dependencies=[Depends(verify_github_signature)])
        async def github_webhook(request: Request):
            # The signature is already verified
            payload = await request.json()
            # Process webhook...
    """
    signature_header = request.headers.get("X-Hub-Signature-256")
    
    if not signature_header:
        raise HTTPException(
            status_code=401, 
            detail="Missing X-Hub-Signature-256 header"
        )
    
    # Get the payload body
    payload_body = await request.body()
    
    # Create hmac signature using webhook secret
    secret = settings.github_webhook_secret.encode()
    signature = "sha256=" + hmac.new(
        secret, 
        payload_body, 
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison to prevent timing attacks)
    if not hmac.compare_digest(signature, signature_header):
        raise HTTPException(
            status_code=401, 
            detail="Invalid webhook signature"
        )
    
    # Reset the request body for further processing
    request._body = payload_body
