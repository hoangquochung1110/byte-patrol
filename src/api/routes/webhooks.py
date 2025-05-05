from fastapi import APIRouter, Request, Header, HTTPException, Depends, BackgroundTasks
from pydantic import ValidationError
import logging
import json
import hmac
import hashlib

from api.services.github import GitHubService
from api.services.code_review import CodeReviewService
from api.models import (
    PullRequestEvent, 
    IssueCommentEvent, 
    PushEvent,
    PingEvent
)
from api.config import get_settings, Settings

router = APIRouter()
logger = logging.getLogger("byte-patrol.webhooks")

def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature_header:
        return False
        
    signature = "sha256=" + hmac.new(
        secret.encode(), 
        payload_body, 
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, signature_header)

@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    settings: Settings = Depends(get_settings),
    github_service: GitHubService = Depends(),
    code_review_service: CodeReviewService = Depends(),
):
    """
    Handle GitHub webhook events.
    This endpoint verifies the webhook signature and processes different event types.
    """
    # Get raw request body
    body = await request.body()
    
    # Verify webhook signature
    if not verify_signature(body, x_hub_signature_256, settings.github_webhook_secret):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    breakpoint()
    # Parse webhook payload
    try:
        payload = json.loads(body)
        logger.info(f"Received {x_github_event} event from GitHub")
        
        # Handle ping event (sent when webhook is first configured)
        if x_github_event == "ping":
            event = PingEvent(**payload)
            return {"message": "pong", "hook_id": event.hook_id}
            
        # Handle issue comment events (for comment-based triggers)
        elif x_github_event == "issue_comment":
            event = IssueCommentEvent(**payload)
            
            # Check if this is a PR comment (not an issue comment)
            if event.issue.pull_request is None:
                return {"message": "Ignored - not a pull request comment"}
                
            # Check if comment contains a review command
            command = github_service.parse_review_command(event.comment.body)
            if command:
                # Process in background to avoid timeout
                background_tasks.add_task(
                    github_service.process_review_command,
                    event,
                    command,
                    code_review_service
                )
                return {
                    "message": "Review started", 
                    "command": command,
                    "pr": event.issue.number
                }
            
            return {"message": "Ignored - no review command found"}
            
        # Handle pull request events
        elif x_github_event == "pull_request":
            event = PullRequestEvent(**payload)
            
            # Only process certain PR actions
            if event.action in ["opened", "synchronize", "reopened"]:
                # Check if auto-review is enabled for this repository
                if github_service.should_auto_review(event.repository.full_name):
                    background_tasks.add_task(
                        github_service.process_pull_request,
                        event,
                        code_review_service
                    )
                    return {
                        "message": "Auto-review started", 
                        "pr": event.number
                    }
            
            return {"message": f"PR {event.action} - no action taken"}
            
        # Other event types can be added here
        
        return {"message": f"Event {x_github_event} received but not processed"}
        
    except ValidationError as e:
        logger.error(f"Invalid webhook payload: {str(e)}")
        return {"error": "Invalid payload format", "details": str(e)}
    except Exception as e:
        logger.exception(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
