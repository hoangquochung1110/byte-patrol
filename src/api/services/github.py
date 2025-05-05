# GitHub API interactions
from fastapi import Depends
import logging
import re
import jwt
import time
import httpx
from typing import Optional, Dict, Any, List, Tuple
import shlex

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
        private_key = self.settings.github_private_key.replace("\\n", "\n")
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
        # Tokenize comment and locate 'review' command
        tokens = shlex.split(comment)
        try:
            idx = tokens.index("review")
        except ValueError:
            return None
        args = tokens[idx+1:]
        files: List[str] = []
        areas: List[str] = []
        style: Optional[str] = None
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ("-a", "--areas", "-areas"):
                if i + 1 < len(args):
                    areas.append(args[i+1])
                    i += 2
                    continue
            elif arg in ("-s", "--style"):
                if i + 1 < len(args):
                    style = args[i+1]
                    i += 2
                    continue
            elif re.match(r"[\w./\-]+\.[A-Za-z0-9]+", arg):
                files.append(arg)
            i += 1
        return {
            "type": "review",
            "files": files,
            "areas": areas,
            "style": style,
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
    ) -> int:
        """Post a comment on a pull request"""
        payload = {"body": comment}
        response = await client.post(
            f"/repos/{repo}/issues/{pr_number}/comments",
            json=payload
        )
        
        if response.status_code != 201:
            logger.error(f"Failed to post comment: {response.text}")
            raise Exception(f"GitHub API error: {response.status_code}")
        
        data = response.json()
        return data
    
    async def edit_review_comment(
        self,
        client: httpx.AsyncClient,
        repo: str,
        comment_id: int,
        new_comment: str
    ) -> None:
        """Edit an existing PR review comment"""
        payload = {"body": new_comment}
        response = await client.patch(
            f"/repos/{repo}/issues/comments/{comment_id}",
            json=payload
        )

        if response.status_code != 200:
            logger.error(f"Failed to edit comment {comment_id}: {response.text}")
            raise Exception(f"GitHub API error: {response.status_code}")
    
    async def process_review_command(
        self,
        event: IssueCommentEvent,
        command: Dict[str, Any],
        code_review_service: CodeReviewService
    ) -> None:
        """Process a review command from a comment"""
        try:
            client = await self.get_client(event.installation.id)
            repo = event.repository.full_name
            pr_number = event.issue.number

            # Fetch existing bot comment for create-or-update
            comments_resp = await client.get(f"/repos/{repo}/issues/{pr_number}/comments")
            if comments_resp.status_code != 200:
                logger.error(f"Failed to list comments: {comments_resp.text}")
                raise Exception(f"GitHub API error: {comments_resp.status_code}")
            existing_comments = comments_resp.json()
            existing_bot = next(
                (c for c in existing_comments if c["body"].startswith("## Byte Patrol Code Review")),
                None
            )

            # Get PR files
            files = await self.get_pull_request_files(client, repo, pr_number)
            if command["files"]:
                files = [f for f in files if f["filename"] in command["files"]]
            if not files:
                body = "❌ No matching files found to review."
                if existing_bot:
                    await self.edit_review_comment(client, repo, existing_bot["id"], body)
                else:
                    await self.post_review_comment(client, repo, pr_number, body)
                return

            # Prepare review parameters
            areas_arg = command.get("areas") or None
            style_arg = command.get("style")
            json_flag = False
            severity_threshold = 0

            # Aggregate reviews and post/update a single comment
            sections = []
            for f in files:
                if f["status"] == "removed":
                    continue
                content = await self.get_file_content(client, repo, f["filename"], event.repository.default_branch)
                result = await code_review_service.review_code(
                    content,
                    f["filename"],
                    areas_arg,
                    style_arg,
                )
                sections.append(f"### {f['filename']}\n\n{result}")
            full_body = "## Byte Patrol Code Review\n\n" + "\n\n".join(sections)
            if existing_bot:
                await self.edit_review_comment(client, repo, existing_bot["id"], full_body)
            else:
                await self.post_review_comment(client, repo, pr_number, full_body)
            
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