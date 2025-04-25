from langchain.prompts import PromptTemplate
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from pydantic import BaseModel, Field


# Define Pydantic models for structured outputs
class CodeReview(BaseModel):
    issues: list[str] = Field(description="Documentation issues identified in the code")
    suggestions: list[str] = Field(description="Specific suggestions for improvement")
    rating: int = Field(description="Overall documentation quality rating (1-10)")


# Create parsers
cr_parser = PydanticOutputParser(pydantic_object=CodeReview)

# Define prompt templates with structured outputs
cr_prompt = PromptTemplate(
    input_variables=["code", "areas", "style"],
    template=(
        "Review the following code in terms of {areas}.\n"
        "Writing Style: {style}\n"
        "Format instruction: {format_instructions}\n"
        "Code:\n{code}"
    ),
    partial_variables={"format_instructions": cr_parser.get_format_instructions()}
)
