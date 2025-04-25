#!/usr/bin/env python3
"""
CLI entry point for byte-patrol.
"""
import sys
from pathlib import Path

import click

from src.byte_patrol.ai_connector.service import get_structured_output
from src.byte_patrol.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from src.byte_patrol.prompt_engine.prompt_templates import (
    CodeReviewResponse, DocumentationReview, code_review_prompt,
    documentation_review_prompt)


def validate_environment():
    """Validate that required environment variables are set."""
    if not OPENROUTER_API_KEY or not OPENROUTER_BASE_URL:
        click.echo("Error: OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be set in environment.", err=True)
        sys.exit(1)

def validate_file(file_path):
    """Validate that the file exists."""
    if not file_path.exists():
        click.echo(f"Error: File not found: {file_path}", err=True)
        sys.exit(1)

def review_documentation(file_path, timeout, max_tokens):
    """Run documentation review on the specified file."""
    code = file_path.read_text()
    
    # notify user of progress
    click.echo(f"Reviewing documentation for {file_path} (timeout={timeout}s, max_tokens={max_tokens})...")
    
    # Use function calling to get structured output
    llm_kwargs = {"request_timeout": timeout, "max_tokens": max_tokens}
    
    # Format prompt and send to LLM using function calling
    formatted_prompt = documentation_review_prompt.format(code=code)
    documentation_review = get_structured_output(formatted_prompt, DocumentationReview, **llm_kwargs)
    
    # Print the structured output in a readable format
    click.echo("\n=== Documentation Review ===")
    click.echo(f"Rating: {documentation_review.rating}/10")
    
    click.echo("\nIssues:")
    for i, issue in enumerate(documentation_review.issues, 1):
        click.echo(f"{i}. {issue}")
    
    click.echo("\nSuggestions:")
    for i, suggestion in enumerate(documentation_review.suggestions, 1):
        click.echo(f"{i}. {suggestion}")

def review_code(file_path, timeout, max_tokens):
    """Run comprehensive code review on the specified file."""
    code = file_path.read_text()
    
    # notify user of progress
    click.echo(f"Reviewing code quality for {file_path} (timeout={timeout}s, max_tokens={max_tokens})...")
    
    # Use function calling to get structured output
    llm_kwargs = {"request_timeout": timeout, "max_tokens": max_tokens}
    
    # Format prompt and send to LLM using function calling
    formatted_prompt = code_review_prompt.format(code=code)
    code_review = get_structured_output(formatted_prompt, CodeReviewResponse, **llm_kwargs)
    
    # Print the structured output in a readable format
    click.echo("\n=== Code Review ===")
    click.echo(f"Overall Quality: {code_review.overall_quality}/10")
    click.echo(f"Summary: {code_review.summary}")
    
    click.echo("\nFindings:")
    for i, finding in enumerate(code_review.findings, 1):
        click.echo(f"\n{i}. {finding.issue_type.upper()} ({finding.severity})")
        click.echo(f"   Description: {finding.description}")
        if finding.code_snippet:
            click.echo(f"   Code: {finding.code_snippet}")
        if finding.line_numbers:
            click.echo(f"   Lines: {', '.join(map(str, finding.line_numbers))}")
        click.echo(f"   Suggestion: {finding.suggestion}")

@click.group()
def cli():
    """Byte Patrol: AI-powered code review."""
    pass

@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option('--timeout', default=30.0, help='Request timeout in seconds')
@click.option('--max-tokens', default=1000, help='Maximum tokens in response')
def docs(file, timeout, max_tokens):
    """Review code documentation."""
    validate_environment()
    review_documentation(file, timeout, max_tokens)

@cli.command()
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option('--timeout', default=30.0, help='Request timeout in seconds')
@click.option('--max-tokens', default=1000, help='Maximum tokens in response')
def code(file, timeout, max_tokens):
    """Review code quality and best practices."""
    validate_environment()
    review_code(file, timeout, max_tokens)

def main():
    cli()

if __name__ == "__main__":
    main()
