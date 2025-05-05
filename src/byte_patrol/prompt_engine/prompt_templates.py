"""Prompt templates for generating code reviews using LLMs."""
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List


class CodeReview(BaseModel):
    """Structured output for code review."""
    issues: List[str] = Field(
        description="Documentation issues identified in the code",
        default_factory=list
    )
    rating: int = Field(
        description="Overall documentation quality rating (1-10)",
        ge=1,
        le=10
    )


class CodeSuggestion(BaseModel):
    """Structured output for code improvement suggestions."""
    suggestion: str = Field(
        description="Specific suggestion for improvement",
        default=""
    )


class CodeReviewResult(BaseModel):
    """Complete result of a code review operation."""
    file_path: str
    review: CodeReview
    suggestion: CodeSuggestion
    passed: bool = Field(
        description="Whether the code passed the severity threshold"
    )


# Define prompt templates for structured outputs
code_review_prompt = PromptTemplate(
    input_variables=["code", "areas", "style"],
    template=(
        "Review the following code in terms of {areas}.\n"
        "Writing Style: {style}\n\n"
        "Provide a structured output with a list of issues and a quality rating from 1-10.\n"
        "Code:\n{code}"
    )
)

code_suggestion_prompt = PromptTemplate(
    input_variables=["code_review"],
    template="""
    Based on the following code review results:
    {code_review}
    
    Generate specific, actionable suggestions to address each identified issue. 
    Focus on practical improvements that would enhance the code quality.
    Provide concrete examples where appropriate.
    
    Return your response as a single, well-structured suggestion.
    """
)