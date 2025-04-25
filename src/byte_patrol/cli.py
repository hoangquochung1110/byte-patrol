#!/usr/bin/env python3
"""
CLI entry point for byte-patrol.
"""
import argparse
from pathlib import Path
from byte_patrol.config import get_llm, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from byte_patrol.prompt_engine.prompt_templates import documentation_review_prompt
from langchain.schema import HumanMessage

def main():
    parser = argparse.ArgumentParser(
        prog="byte-patrol",
        description="Review code documentation via an LLM"
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to the source code file to review"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=30,
        help="LLM request timeout in seconds"
    )
    parser.add_argument(
        "-m", "--max-tokens",
        type=int,
        default=200,
        help="Maximum number of tokens in the response"
    )
    args = parser.parse_args()

    # ensure file exists
    if not args.file.exists():
        parser.error(f"File {args.file} not found.")

    # ensure LLM env is configured
    if not OPENROUTER_API_KEY or not OPENROUTER_BASE_URL:
        parser.error("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be set in environment.")

    code = args.file.read_text()
    llm = get_llm(request_timeout=args.timeout, max_tokens=args.max_tokens)
    # notify user of progress
    print(f"Reviewing file {args.file} (timeout={args.timeout}s, max_tokens={args.max_tokens})...", flush=True)
    # Format prompt and send to LLM using the pipeline syntax
    documentation_review = (documentation_review_prompt | llm).invoke({"code": code}).content
    print(documentation_review)


if __name__ == "__main__":
    main()
