#!/usr/bin/env python3
"""
CLI entry point for byte-patrol.
"""
from pathlib import Path

import click

from byte_patrol.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, get_llm
from byte_patrol.prompt_engine.prompt_templates import cr_prompt


@click.command(help="Review code documentation via an LLM")
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option('-t', '--timeout', type=float, default=30, help="LLM request timeout in seconds")
@click.option('-m', '--max-tokens', type=int, default=200, help="Maximum number of tokens in the response")
@click.option('-a', '--areas', type=str, default=["documentation"], multiple=True, help="Areas to review (can be specified multiple times)")
def main(file, timeout, max_tokens, areas):
    # ensure LLM env is configured
    if not OPENROUTER_API_KEY or not OPENROUTER_BASE_URL:
        click.echo("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be set in environment.", err=True)
        return 1

    code = file.read_text()
    llm = get_llm(request_timeout=timeout, max_tokens=max_tokens)
    # notify user of progress
    click.echo(f"Reviewing file {file} (timeout={timeout}s, max_tokens={max_tokens})...", nl=True)
    # Format prompt and send to LLM using the pipeline syntax
    areas_str = ", ".join(areas)
    documentation_review = (cr_prompt | llm).invoke({"code": code, "areas": areas_str}).content
    click.echo(documentation_review)
    return 0


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
