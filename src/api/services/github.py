# GitHub API interactions
import logging
import re
import shlex
import time
from typing import Any, Dict, List, Optional, TypeVar, Generic
from argparse import ArgumentParser
import argparse

import httpx
import jwt
from fastapi import Depends
from pathlib import Path

from api.config import Settings, get_settings
from api.models import IssueCommentEvent, PullRequest, PullRequestEvent
from api.services.code_review import CodeReviewService
from api.constants import DEFAULT_FILE_TYPES, DEFAULT_JWT_EXPIRY_SEC

logger = logging.getLogger("byte-patrol.github")

T = TypeVar('T')


class GitHubClient:
    def __init__(self, settings: Settings = Depends(get_settings)):
        self.settings = settings
        self.client = None

    async def _request_json(
        self,
        method: str,
        path: str,
        expected_status: int = 200,
        **kwargs
    ) -> Any:
        """Make an HTTP request and handle JSON response."""
        if self.client is None:
            raise RuntimeError("GitHubClient not initialized. Call 'initialize' first.")
        try:
            response = await self.client.request(method, path, **kwargs)
            response.raise_for_status()
            if response.status_code != expected_status:
                raise httpx.HTTPStatusError(
                    f"Expected status {expected_status}, got {response.status_code}",
                    request=response.request,
                    response=response
                )
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API {method} {path} failed: {e.response.text}")
            raise Exception(f"GitHub API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Request failed for {method} {path}: {str(e)}")
            raise Exception("Failed to connect to GitHub API") from e

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
                response = await client.request(
                    "POST",
                    f"{self.settings.github_api_url}/app/installations/{installation_id}/access_tokens",
                    headers=headers
                )
                if response.status_code != 201:
                    logger.error(
                        f"Failed to get installation token: {response.status_code} {response.text}"
                    )
                    raise Exception(
                        f"Failed to get installation token: {response.status_code} {response.text}"
                    )
                data = response.json()
                if "token" not in data:
                    logger.error(f"Installation token missing in response: {data}")
                    raise Exception("Installation token missing in response")
                return data["token"]
            except httpx.RequestError as e:
                logger.error(f"Request failed for installation token: {str(e)}")
                raise Exception("Failed to connect to GitHub API for installation token") from e

    async def initialize(self, installation_id: int):
        token = await self.get_installation_token(installation_id)
        self.client = httpx.AsyncClient(
            base_url=self.settings.github_api_url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "BytePatrol-GitHub-App"
            },
            timeout=30.0
        )
        return self

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()


class GitHubService:
    def __init__(self, settings: Settings = Depends(get_settings)):
        self.settings = settings

    async def get_client(self, installation_id: int) -> httpx.AsyncClient:
        """Get an authenticated client for GitHub API requests"""
        client = GitHubClient(self.settings)
        client = await client.initialize(installation_id)
        return client

    def parse_review_command(self, comment: str) -> Optional[Dict[str, Any]]:
        """Parse review command from comment text using argparse.
        
        Example commands:
        - review file1.py file2.py
        - review -a security -a performance file1.py
        - review --style detailed -t py,js file1.py file2.js
        
        Available review styles:
        - concise: Brief, focused feedback
        - detailed: Comprehensive analysis
        - strict: Focus on potential issues
        - lenient: Focus on major issues only
        
        Available review areas:
        - security: Security vulnerabilities
        - performance: Performance optimizations
        - maintainability: Code maintainability
        - style: Code style and conventions
        - quality: General code quality
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
        parser = ArgumentParser(
            prog="review",
            add_help=False,
            description="Review code changes in the pull request",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Define command options
        parser.add_argument(
            "-a", "--areas",
            action="append",
            metavar="AREA",
            default=[],
            help="Areas to focus the review on (can repeat). "
                 "Choices: security, performance, maintainability, style, quality"
        )
        parser.add_argument(
            "-s", "--style",
            type=str,
            choices=["concise", "detailed", "strict", "lenient"],
            metavar="STYLE",
            help="Review style guidance. "
                 "Choices: concise (default), detailed, strict, lenient"
        )
        parser.add_argument(
            "-t", "--type", "--file-type",
            dest="file_types",
            type=lambda s: [ext.strip().lstrip('.') for ext in s.split(",")],
            metavar="EXTENSIONS",
            default=list(DEFAULT_FILE_TYPES),
            help=f"Comma-separated file extensions to review (default: {','.join(DEFAULT_FILE_TYPES)})"
        )
        # Any remaining args are treated as filenames
        parser.add_argument(
            "files",
            nargs="*",
            metavar="FILE",
            help="Specific files to review (default: all changed files)"
        )

        try:
            namespace, unknown = parser.parse_known_args(args)
            if unknown:
                logger.warning(f"Ignoring unknown arguments: {unknown}")
            
            # Validate file extensions
            for ext in namespace.file_types:
                if not ext.isalnum():
                    logger.warning(f"Invalid file extension: {ext}")
                    namespace.file_types = list(DEFAULT_FILE_TYPES)
                    break
            
            return {
                "type": "review",
                "files": namespace.files,
                "areas": namespace.areas,
                "style": namespace.style or "concise",  # Default to concise if not specified
                "file_types": namespace.file_types,
            }
        except Exception as e:
            logger.error(f"Failed to parse review command: {str(e)}")
            return None
    
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
            file_types = command.get("file_types", list(DEFAULT_FILE_TYPES))
            code_review_service.set_allowed_file_types(file_types)

            # Fetch existing bot comment for create-or-update
            try:
                comments = await client._request_json(
                    "GET",
                    f"/repos/{repo}/issues/{pr_number}/comments"
                )
                existing_bot = next(
                    (c for c in comments if c["body"].startswith("## Byte Patrol Code Review")),
                    None
                )
            except Exception as e:
                logger.error(f"Failed to list comments: {str(e)}")
                raise

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
                pr_data = await client._request_json(
                    "GET",
                    f"/repos/{repo}/pulls/{pr_number}"
                )
                pr = PullRequest(**pr_data)
                ref = pr.head.ref
            except Exception as e:
                logger.error(f"Failed to get PR metadata: {str(e)}")
                raise

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

    def should_auto_review(self, repo_full_name: str) -> bool:
        """Check if auto-review is enabled for this repository"""
        # This could be enhanced to check against a database or config file
        # For now, just a simple example
        auto_review_repos = ["your-org/your-repo"]
        return repo_full_name in auto_review_repos
    
    async def get_pull_request_files(
        self, 
        client: "GithubClient",
        repo: str, 
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """Get files modified in a pull request"""
        return await client._request_json(
            "GET",
            f"/repos/{repo}/pulls/{pr_number}/files"
        )

    async def get_file_content(
        self, 
        client: "GithubClient",
        repo: str, 
        file_path: str, 
        ref: str
    ) -> str:
        """Get content of a file from GitHub"""
        data = await client._request_json(
            "GET",
            f"/repos/{repo}/contents/{file_path}",
            params={"ref": ref}
        )
        import base64
        return base64.b64decode(data["content"]).decode("utf-8")
    
    async def post_review_comment(
        self, 
        client: "GithubClient",
        repo: str, 
        pr_number: int, 
        comment: str
    ) -> int:
        """Post a comment on a pull request"""
        payload = {"body": comment}
        return await client._request_json(
            "POST",
            f"/repos/{repo}/issues/{pr_number}/comments",
            expected_status=201,
            json=payload
        )
    
    async def edit_review_comment(
        self,
        client: "GithubClient",
        repo: str,
        comment_id: int,
        new_comment: str
    ) -> None:
        """Edit an existing PR review comment"""
        payload = {"body": new_comment}
        await client._request_json(
            "PATCH",
            f"/repos/{repo}/issues/comments/{comment_id}",
            json=payload
        )
