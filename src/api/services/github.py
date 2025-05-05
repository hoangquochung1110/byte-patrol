# GitHub API interactions
from fastapi import Depends
import logging
import re
import jwt
import time
import httpx
from typing import Optional, Dict, Any, List, Tuple

from api.models import IssueCommentEvent, PullRequestEvent
from api.services.code_review import CodeReviewService
from api.config import get_settings, Settings

logger = logging.getLogger("byte-patrol.github")

class GitHubService:
    def __init__(self, settings: Settings = Depends(get_settings)):
        self.settings = settings
        self.base_url = settings.github_api_url
        
    async def get_installation_token(self, installation_id: int) -> str:
        """Generate a JWT and exchange it for an installation token"""
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + (10 * 60),  # 10 minutes expiration
            "iss": self.settings.github_app_id
        }
        
        # Create JWT
        private_key = self.settings.github_app_private_key.replace("\\n", "\n")
        jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
        
        # Exchange JWT for installation token
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = await client.post(
                f"{self.base_url}/app/installations/{installation_id}/access_tokens",
                headers=headers
            )
            
            if response.status_code != 201:
                logger.error(f"Failed to get installation token: {response.text}")
                raise Exception(f"GitHub API error: {response.status_code}")
                
            data = response.json()
            return data["token"]
    
    async def get_client(self, installation_id: int) -> httpx.AsyncClient:
        """Get an authenticated client for GitHub API requests"""
        token = await self.get_installation_token(installation_id)
        
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "BytePatrol-GitHub-App"
            },
            timeout=30.0
        )
    
    def parse_review_command(self, comment: str) -> Optional[Dict[str, Any]]:
        """Parse review command from comment text"""
        # Match pattern: @byte-patrol review [file1.py] [file2.py]
        pattern = r"@byte-patrol\s+review(?:\s+([^\s]+))?"
        match = re.search(pattern, comment, re.IGNORECASE)
        
        if not match:
            return None
            
        # Extract files to review (if specified)
        files_str = match.group(1)
        files = []
        if files_str:
            files = re.findall(r"[\w./\-]+\.\w+", files_str)
            
        return {
            "type": "review",
            "files": files or []  # Empty list means review all files
        }
    
    def should_auto_review(self, repo_full_name: str) -> bool:
        """Check if auto-review is enabled for this repository"""
        # This could be enhanced to check against a database or config file
        # For now, just a simple example
        auto_review_repos = ["your-org/your-repo"]
        return repo_full_name in auto_review_repos
    
    async def get_pull_request_files(
        self, 
        client: httpx.AsyncClient,
        repo: str, 
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """Get files modified in a pull request"""
        response = await client.get(f"/repos/{repo}/pulls/{pr_number}/files")
        
        if response.status_code != 200:
            logger.error(f"Failed to get PR files: {response.text}")
            raise Exception(f"GitHub API error: {response.status_code}")
            
        return response.json()
    
    async def get_file_content(
        self, 
        client: httpx.AsyncClient,
        repo: str, 
        file_path: str, 
        ref: str
    ) -> str:
        """Get content of a file from GitHub"""
        response = await client.get(
            f"/repos/{repo}/contents/{file_path}",
            params={"ref": ref}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get file content: {response.text}")
            raise Exception(f"GitHub API error: {response.status_code}")
            
        data = response.json()
        import base64
        return base64.b64decode(data["content"]).decode("utf-8")
    
    async def post_review_comment(
        self, 
        client: httpx.AsyncClient,
        repo: str, 
        pr_number: int, 
        comment: str
    ) -> None:
        """Post a comment on a pull request"""
        payload = {"body": comment}
        response = await client.post(
            f"/repos/{repo}/issues/{pr_number}/comments",
            json=payload
        )
        
        if response.status_code != 201:
            logger.error(f"Failed to post comment: {response.text}")
            raise Exception(f"GitHub API error: {response.status_code}")
    
    async def process_review_command(
        self,
        event: IssueCommentEvent,
        command: Dict[str, Any],
        code_review_service: CodeReviewService
    ) -> None:
        """Process a review command from a comment"""
        try:
            # Initialize GitHub client
            client = await self.get_client(event.installation.id)
            
            # Get PR details
            repo = event.repository.full_name
            pr_number = event.issue.number
            
            # Post initial comment to acknowledge
            await self.post_review_comment(
                client,
                repo,
                pr_number,
                "🔍 Byte Patrol is reviewing your code. Please wait..."
            )
            
            # Get PR files
            files = await self.get_pull_request_files(client, repo, pr_number)
            
            # Filter files based on command
            if command["files"]:
                files = [f for f in files if f["filename"] in command["files"]]
            
            if not files:
                await self.post_review_comment(
                    client,
                    repo,
                    pr_number,
                    "❌ No matching files found to review."
                )
                return
            
            # Review each file
            for file in files:
                # Skip deleted files
                if file["status"] == "removed":
                    continue
                    
                # Get file content
                content = await self.get_file_content(
                    client,
                    repo,
                    file["filename"],
                    event.repository.default_branch
                )
                
                # Perform review
                review_result = await code_review_service.review_code(
                    content,
                    file["filename"]
                )
                
                # Post review as comment
                await self.post_review_comment(
                    client,
                    repo,
                    pr_number,
                    f"## Code Review: {file['filename']}\n\n{review_result}"
                )
            
            # Post summary
            await self.post_review_comment(
                client,
                repo,
                pr_number,
                f"✅ Code review completed for {len(files)} files."
            )
            
        except Exception as e:
            logger.exception(f"Error processing review command: {str(e)}")
            try:
                await self.post_review_comment(
                    client,
                    repo,
                    pr_number,
                    f"❌ Error during code review: {str(e)}"
                )
            except:
                pass