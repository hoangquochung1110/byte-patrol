from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional

# Define Pydantic models for structured outputs
class DocumentationReview(BaseModel):
    issues: List[str] = Field(description="Documentation issues identified in the code")
    suggestions: List[str] = Field(description="Specific suggestions for improvement")
    rating: int = Field(description="Overall documentation quality rating (1-10)")

class CodeReviewFinding(BaseModel):
    issue_type: str = Field(description="Category of the issue (e.g., 'documentation', 'performance', 'security')")
    severity: str = Field(description="Severity level (critical, high, medium, low)")
    description: str = Field(description="Detailed explanation of the issue")
    code_snippet: Optional[str] = Field(description="Relevant code causing the issue", default=None)
    suggestion: str = Field(description="Recommended fix or improvement")
    line_numbers: Optional[List[int]] = Field(description="Affected line numbers", default=None)

class CodeReviewResponse(BaseModel):
    findings: List[CodeReviewFinding] = Field(description="List of code review findings")
    overall_quality: int = Field(description="Overall code quality score (1-10)")
    summary: str = Field(description="Brief summary of the review")

# Create parsers
documentation_parser = PydanticOutputParser(pydantic_object=DocumentationReview)
code_review_parser = PydanticOutputParser(pydantic_object=CodeReviewResponse)

# Define prompt templates with structured outputs
documentation_review_prompt = PromptTemplate(
    input_variables=["code"],
    template="Review the following code in terms of good documentation. Be concise and focus only on the most important aspects.\n{format_instructions}\nCode:\n{code}",
    partial_variables={"format_instructions": documentation_parser.get_format_instructions()}
)

code_review_prompt = PromptTemplate(
    input_variables=["code"],
    template="Review the following code for quality, best practices, and potential issues.\n{format_instructions}\nCode:\n{code}",
    partial_variables={"format_instructions": code_review_parser.get_format_instructions()}
)

# Additional prompt templates can be added here as needed
