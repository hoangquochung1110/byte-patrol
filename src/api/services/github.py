# GitHub API interactions
import logging
import re
import shlex
import time
from typing import Any, Dict, List, Optional
from argparse import ArgumentParser

import httpx
import jwt
from fastapi import Depends
from pathlib import Path

from api.config import Settings, get_settings
from api.models import IssueCommentEvent, PullRequest, PullRequestEvent
from api.services.code_review import CodeReviewService

logger = logging.getLogger("byte-patrol.github")

# how long our JWT should live, in seconds
DEFAULT_JWT_EXPIRY_SEC = 10 * 60

class GitHubService:
    def __init__(self, settings: Settings = Depends(get_settings)):
        self.settings = settings
        self.base_url = settings.github_api_url
        
    async def get_installation_token(self, installation_id: int) -> str:
        """Generate a JWT and exchange it for an installation token"""
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + DEFAULT_JWT_EXPIRY_SEC,  # 10 minutes expiration
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
            
            try:
                response = await client.post(
                    f"{self.base_url}/app/installations/{installation_id}/access_tokens",
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return data["token"]
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get installation token: {e.response.text}")
                raise Exception(f"GitHub API error: {e.response.status_code}") from e
            except httpx.RequestError as e:
                logger.error(f"Request failed while getting installation token: {str(e)}")
                raise Exception("Failed to connect to GitHub API") from e
    
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
        """Parse review command from comment text using argparse.
        
        Example commands:
        - review file1.py file2.py
        - review -a security -a performance file1.py
        - review --style detailed -t py,js file1.py file2.js
        """
        # Tokenize comment and locate 'review' command
        tokens = shlex.split(comment)
        try:
            idx = tokens.index("review")
        except ValueError:
            logger.debug("No review command found in comment: %s ...", comment[:20])
            return None

        # Parse arguments after 'review'
        args = tokens[idx+1:]
        parser = ArgumentParser(prog="review", add_help=False)
        
        # Define command options
        parser.add_argument(
            "-a", "--areas",
            action="append",
            default=[],
            help="Areas to focus the review on (can repeat)"
        )
        parser.add_argument(
            "-s", "--style",
            type=str,
            help="Review style guidance"
        )
        parser.add_argument(
            "-t", "--type", "--file-type",
            dest="file_types",
            type=lambda s: s.split(","),
            default=["py"],
            help="Comma-separated file extensions to review"
        )
        # Any remaining args are treated as filenames
        parser.add_argument(
            "files",
            nargs="*",
            help="Specific filenames to review"
        )

        try:
            namespace, unknown = parser.parse_known_args(args)
            if unknown:
                logger.warning(f"Ignoring unknown arguments: {unknown}")
            
            return {
                "type": "review",
                "files": namespace.files,
                "areas": namespace.areas,
                "style": namespace.style,
                "file_types": namespace.file_types,
            }
        except Exception as e:
            logger.error(f"Failed to parse review command: {str(e)}")
            return None
    
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
        try:
            response = await client.get(f"/repos/{repo}/pulls/{pr_number}/files")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get PR files: {e.response.text}")
            raise Exception(f"GitHub API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Request failed while getting PR files: {str(e)}")
            raise Exception("Failed to connect to GitHub API") from e
    
    async def get_file_content(
        self, 
        client: httpx.AsyncClient,
        repo: str, 
        file_path: str, 
        ref: str
    ) -> str:
        """Get content of a file from GitHub"""
        try:
            response = await client.get(
                f"/repos/{repo}/contents/{file_path}",
                params={"ref": ref}
            )
            response.raise_for_status()
            data = response.json()
            import base64
            return base64.b64decode(data["content"]).decode("utf-8")
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get file content: {e.response.text}")
            raise Exception(f"GitHub API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Request failed while getting file content: {str(e)}")
            raise Exception("Failed to connect to GitHub API") from e
    
    async def post_review_comment(
        self, 
        client: httpx.AsyncClient,
        repo: str, 
        pr_number: int, 
        comment: str
    ) -> int:
        """Post a comment on a pull request"""
        try:
            payload = {"body": comment}
            response = await client.post(
                f"/repos/{repo}/issues/{pr_number}/comments",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to post comment: {e.response.text}")
            raise Exception(f"GitHub API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Request failed while posting comment: {str(e)}")
            raise Exception("Failed to connect to GitHub API") from e
    
    async def edit_review_comment(
        self,
        client: httpx.AsyncClient,
        repo: str,
        comment_id: int,
        new_comment: str
    ) -> None:
        """Edit an existing PR review comment"""
        try:
            payload = {"body": new_comment}
            response = await client.patch(
                f"/repos/{repo}/issues/comments/{comment_id}",
                json=payload
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to edit comment {comment_id}: {e.response.text}")
            raise Exception(f"GitHub API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Request failed while editing comment: {str(e)}")
            raise Exception("Failed to connect to GitHub API") from e
    
    async def process_review_command(
        self,
        event: IssueCommentEvent,
        command: Dict[str, Any],
        code_review_service: CodeReviewService
    ) -> None:
        """Process a review command from a comment"""
        client = None
        try:
            # Create single client for all operations
            client = await self.get_client(event.installation.id)
            repo = event.repository.full_name
            pr_number = event.issue.number

            # Set allowed file types for review
            file_types = command.get("file_types", ["py"])
            code_review_service.set_allowed_file_types(file_types)

            # Fetch existing bot comment for create-or-update
            try:
                comments_resp = await client.get(f"/repos/{repo}/issues/{pr_number}/comments")
                comments_resp.raise_for_status()
                existing_comments = comments_resp.json()
                existing_bot = next(
                    (c for c in existing_comments if c["body"].startswith("## Byte Patrol Code Review")),
                    None
                )
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to list comments: {e.response.text}")
                raise Exception(f"GitHub API error: {e.response.status_code}") from e
            except httpx.RequestError as e:
                logger.error(f"Request failed while listing comments: {str(e)}")
                raise Exception("Failed to connect to GitHub API") from e

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

            # Fetch PR metadata once
            try:
                pr_resp = await client.get(f"/repos/{repo}/pulls/{pr_number}")
                pr_resp.raise_for_status()
                pr = PullRequest(**pr_resp.json())
                ref = pr.head.ref
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get PR metadata: {e.response.text}")
                raise Exception(f"GitHub API error: {e.response.status_code}") from e
            except httpx.RequestError as e:
                logger.error(f"Request failed while getting PR metadata: {str(e)}")
                raise Exception("Failed to connect to GitHub API") from e

            # Prepare review parameters
            areas_arg = command.get("areas") or None
            style_arg = command.get("style")

            # Aggregate reviews and post/update a single comment
            sections = []
            reviewed_count = 0
            skipped_count = 0

            for f in files:
                if f["status"] == "removed":
                    continue
                try:
                    content = await self.get_file_content(client, repo, f["filename"], ref)
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    logger.error(f"Failed to get file content for {f['filename']}: {str(e)}")
                    continue
                else:
                    try:
                        result = await code_review_service.review_code(
                            content,
                            f["filename"],
                            areas_arg,
                            style_arg,
                        )
                        if "Skipping review: File type not supported" in result:
                            skipped_count += 1
                        else:
                            reviewed_count += 1
                            sections.append(f"### {f['filename']}\n\n{result}")
                    except Exception as e:
                        logger.error(f"Failed to review file {f['filename']}: {str(e)}")
                        continue

            # Create summary header
            summary = [
                "## Byte Patrol Code Review\n",
                f"Reviewing files with types: {', '.join(file_types)}\n",
                f"Files reviewed: {reviewed_count}\n",
                f"Files skipped: {skipped_count}\n\n"
            ]

            full_body = "".join(summary) + "\n\n".join(sections)
            if existing_bot:
                await self.edit_review_comment(client, repo, existing_bot["id"], full_body)
            else:
                await self.post_review_comment(client, repo, pr_number, full_body)
            
        except Exception as e:
            logger.exception(f"Error processing review command: {str(e)}")
            if client:
                try:
                    await self.post_review_comment(
                        client,
                        repo,
                        pr_number,
                        f"❌ Error during code review: {str(e)}"
                    )
                except Exception as comment_error:
                    logger.error(f"Failed to post error comment: {str(comment_error)}")