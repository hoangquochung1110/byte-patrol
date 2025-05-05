#!/usr/bin/env python3
"""
CLI entry point for byte-patrol.
"""
from pathlib import Path

import click

from byte_patrol.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, get_llm
from byte_patrol.prompt_engine.prompt_templates import (CodeReview,
                                                        CodeReviewResult,
                                                        CodeSuggestion,
                                                        code_review_prompt,
                                                        code_suggestion_prompt)


@click.command(help="Review code documentation via an LLM")
@click.argument('file', type=click.Path(exists=True, path_type=Path))
@click.option('-t', '--timeout', type=float, default=30, help="LLM request timeout in seconds")
@click.option('-m', '--max-tokens', type=int, default=200, help="Maximum number of tokens in the response")
@click.option('-a', '--areas', type=str, default=["documentation"], multiple=True, help="Areas to review (can be specified multiple times)")
@click.option('-s', '--style', type=str, default="Be concise and focus only on the most important aspects.", 
              help="Customize the style of the response (e.g., 'Be very detailed', 'Keep it brief', etc.)")
@click.option('--severity-threshold', type=int, default=0, 
              help="Minimum severity to fail the commit (1-10)")
@click.option('--json', is_flag=True, help="Output in JSON format")
def main(
    file,
    areas,
    style,
    timeout,
    max_tokens,
    json,
    severity_threshold,
):
    """Review code using AI and return structured feedback."""
    # ensure LLM env is configured
    if not OPENROUTER_API_KEY or not OPENROUTER_BASE_URL:
        click.echo("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must be set in environment.", err=True)
        return 1
        
    # Skip non-Python files if python_only is set
    if python_only and file.suffix != '.py':
        click.echo(f"Skipping non-Python file: {file}")
        return 0

    code = file.read_text()
    llm = get_llm(request_timeout=timeout, max_tokens=max_tokens)
    
    # Setup structured output capabilities
    review_llm = llm.with_structured_output(CodeReview)
    suggestion_llm = llm.with_structured_output(CodeSuggestion)

    # notify user of progress
    click.echo(f"Reviewing file {file} (timeout={timeout}s, max_tokens={max_tokens})...", nl=True)
    
    # Run the LLM pipeline with structured outputs
    areas_str = ", ".join(areas)
    review_result = (code_review_prompt | review_llm).invoke(
        {"code": code, "areas": areas_str, "style": style}
    )
    
    suggestion_result = (code_suggestion_prompt | suggestion_llm).invoke(
        {"code_review": review_result.model_dump_json()}
    )
    
    # Determine if the review passes the severity threshold
    passed = review_result.rating > severity_threshold
    
    # Create the final structured result
    result = CodeReviewResult(
        file_path=str(file),
        review=review_result,
        suggestion=suggestion_result,
        passed=passed
    )
    
    # Output the results
    if json:
        click.echo(result.model_dump_json(indent=2))
    else:
        click.echo(f"File: {file}")
        click.echo(f"Rating: {review_result.rating}/10")
        click.echo("Issues:")
        for issue in review_result.issues:
            click.echo(f"- {issue}")
        click.echo("\nSuggestion:")
        click.echo(suggestion_result.suggestion)
        click.echo(f"\nPassed: {'✅' if passed else '❌'}")
    
    # Return non-zero exit code if failed
    return 0 if passed else 1


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
