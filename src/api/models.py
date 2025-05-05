from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# Base GitHub models
class GitHubUser(BaseModel):
    login: str
    id: int
    
class Repository(BaseModel):
    id: int
    name: str
    full_name: str
    default_branch: str
    
class Installation(BaseModel):
    id: int

# Ping event
class PingEvent(BaseModel):
    zen: str
    hook_id: int
    repository: Repository
    sender: GitHubUser
    installation: Optional[Installation] = None

# Issue/PR models
class PullRequestRef(BaseModel):
    url: str
    
class Issue(BaseModel):
    number: int
    title: str
    user: GitHubUser
    pull_request: Optional[PullRequestRef] = None
    
class Comment(BaseModel):
    id: int
    user: GitHubUser
    body: str
    created_at: datetime

# Issue comment event
class IssueCommentEvent(BaseModel):
    action: str
    issue: Issue
    comment: Comment
    repository: Repository
    sender: GitHubUser
    installation: Installation

# PR models
class PullRequestBase(BaseModel):
    ref: str
    sha: str
    
class PullRequest(BaseModel):
    number: int
    title: str
    user: GitHubUser
    body: Optional[str] = None
    head: PullRequestBase
    base: PullRequestBase
    
# PR event
class PullRequestEvent(BaseModel):
    action: str
    number: int
    pull_request: PullRequest
    repository: Repository
    sender: GitHubUser
    installation: Installation

# Push event models
class Commit(BaseModel):
    id: str
    message: str
    author: Dict[str, Any]
    
class PushEvent(BaseModel):
    ref: str
    before: str
    after: str
    repository: Repository
    sender: GitHubUser
    installation: Installation
    commits: List[Commit]
