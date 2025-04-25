#!/usr/bin/env python3
"""
CLI entry point for byte-patrol.
"""
import argparse
import os
import sys
from pathlib import Path

from src.byte_patrol.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from src.byte_patrol.prompt_engine.prompt_templates import DocumentationReview, CodeReviewResponse, documentation_review_prompt, code_review_prompt
from src.byte_patrol.ai_connector.service import get_structured_output

def main():
    parser = argparse.ArgumentParser(description="Byte Patrol: AI-powered code review")
    parser.add_argument("file", type=Path, help="Path to the file to review")
    parser.add_argument("--timeout", type=float, default=30, help="Request timeout in seconds")
    parser.add_argument("--max-tokens", type=int, default=1000, help="Maximum tokens in response")
    args = parser.parse_args()

    # Validate file exists
    if not args.file.exists():
        parser.error(f"File not found: {args.file}")

    # Check for API credentials
    if not OPENROUTER_API_KEY or not OPENROUTER_BASE_URL:
        parser.error("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be set in environment.")

    code = args.file.read_text()
    
    # notify user of progress
    print(f"Reviewing file {args.file} (timeout={args.timeout}s, max_tokens={args.max_tokens})...", flush=True)
    
    # Use function calling to get structured output
    llm_kwargs = {"request_timeout": args.timeout, "max_tokens": args.max_tokens}
    
    # Format prompt and send to LLM using function calling
    formatted_prompt = documentation_review_prompt.format(code=code)
    documentation_review = get_structured_output(formatted_prompt, DocumentationReview, **llm_kwargs)
    
    # Print the structured output in a readable format
    print("\n=== Documentation Review ===")
    print(f"Rating: {documentation_review.rating}/10")
    
    print("\nIssues:")
    for i, issue in enumerate(documentation_review.issues, 1):
        print(f"{i}. {issue}")
    
    print("\nSuggestions:")
    for i, suggestion in enumerate(documentation_review.suggestions, 1):
        print(f"{i}. {suggestion}")


if __name__ == "__main__":
    main()
