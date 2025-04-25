from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional

# Define Pydantic models for structured outputs
class DocumentationReview(BaseModel):
    issues: List[str] = Field(description="Documentation issues identified in the code")
    suggestions: List[str] = Field(description="Specific suggestions for improvement")
    rating: int = Field(description="Overall documentation quality rating (1-10)")


# Create parsers
documentation_parser = PydanticOutputParser(pydantic_object=DocumentationReview)

# Define prompt templates with structured outputs
documentation_review_prompt = PromptTemplate(
    input_variables=["code", "areas"],
    template=(
        "Review the following code in terms of {areas}. "
        "Be concise and focus only on the most important aspects.\n{format_instructions}\nCode:\n{code}"
    ),
    partial_variables={"format_instructions": documentation_parser.get_format_instructions()}
)
