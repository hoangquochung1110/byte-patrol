from langchain.prompts import PromptTemplate
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from pydantic import BaseModel, Field


# Define Pydantic models for structured outputs
class CodeReview(BaseModel):
    issues: list[str] = Field(description="Documentation issues identified in the code")
    rating: int = Field(description="Overall documentation quality rating (1-10)")


class CodeSuggestion(BaseModel):
    suggestion: str = Field(description="Specific suggestion for improvement")


# Create parsers
code_review_parser = PydanticOutputParser(pydantic_object=CodeReview)
code_suggestion_parser = PydanticOutputParser(pydantic_object=CodeSuggestion)

# Define prompt templates with structured outputs
code_review_prompt = PromptTemplate(
    input_variables=["code", "areas", "style"],
    template=(
        "Review the following code in terms of {areas}.\n"
        "Writing Style: {style}\n"
        "Format instruction: {format_instructions}\n"
        "Code:\n{code}"
    ),
    partial_variables={"format_instructions": code_review_parser.get_format_instructions()}
)

code_suggestion_prompt = PromptTemplate(
    input_variables=["code_review"],
    template="""
    Based on the following code review results:
    {code_review}
    
    Generate specific, actionable suggestions to address each identified issue. 
    Focus on practical improvements that would enhance the code quality.
    Provide concrete examples where appropriate.
    
    {format_instructions}
    """,
    partial_variables={"format_instructions": code_suggestion_parser.get_format_instructions()}
)
