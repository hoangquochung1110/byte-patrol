"""Example usage of structured prompt templates with Pydantic models."""

import json
import re
from byte_patrol.prompt_engine.prompt_templates import (
    documentation_review_prompt,
    code_review_prompt,
    DocumentationReview,
    CodeReviewResponse
)
from byte_patrol.config import get_llm
from langchain.schema import HumanMessage
from langchain_core.exceptions import OutputParserException

def extract_json_from_llm_response(text: str) -> dict:
    """
    Extract JSON from LLM response text, which might contain markdown or other formatting.
    
    Args:
        text: The raw text response from the LLM
        
    Returns:
        dict: Extracted JSON object or empty dict if parsing fails
    """
    # Try to find JSON blocks in markdown (```json ... ```)
    json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    json_matches = re.findall(json_pattern, text)
    
    if json_matches:
        for json_str in json_matches:
            try:
                return json.loads(json_str.strip())
            except json.JSONDecodeError:
                continue
    
    # If no markdown blocks or they didn't parse, try the entire text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Last resort: try to find anything that looks like a JSON object
    try:
        json_pattern = r"\{[\s\S]*\}"
        json_match = re.search(json_pattern, text)
        if json_match:
            return json.loads(json_match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass
    
    return {}

def review_code_documentation(code: str):
    """
    Review code documentation using structured output.
    
    Args:
        code: The code to review
    
    Returns:
        DocumentationReview: Structured review of documentation or None if parsing fails
    """
    # Format the prompt with the code
    prompt = documentation_review_prompt.format(code=code)
    
    # Get the LLM with appropriate settings for structured output
    llm = get_llm(max_tokens=1000)
    
    # Send the prompt to the LLM
    ai_message = llm.invoke([HumanMessage(content=prompt)])
    
    # Extract and parse JSON from the response
    try:
        json_data = extract_json_from_llm_response(ai_message.content)
        if not json_data:
            print("Warning: Could not extract valid JSON from LLM response")
            return None
            
        # Create Pydantic model from the extracted JSON
        return DocumentationReview.model_validate(json_data)
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Raw response: {ai_message.content}")
        return None

def perform_code_review(code: str):
    """
    Perform a comprehensive code review using structured output.
    
    Args:
        code: The code to review
    
    Returns:
        CodeReviewResponse: Structured code review or None if parsing fails
    """
    # Format the prompt with the code
    prompt = code_review_prompt.format(code=code)
    
    # Get the LLM with appropriate settings for structured output
    llm = get_llm(max_tokens=2000)
    
    # Send the prompt to the LLM
    ai_message = llm.invoke([HumanMessage(content=prompt)])
    
    # Extract and parse JSON from the response
    try:
        json_data = extract_json_from_llm_response(ai_message.content)
        if not json_data:
            print("Warning: Could not extract valid JSON from LLM response")
            return None
            
        # Create Pydantic model from the extracted JSON
        return CodeReviewResponse.model_validate(json_data)
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Raw response: {ai_message.content}")
        return None

# Example usage
if __name__ == "__main__":
    sample_code = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total
    """
    
    # Get structured documentation review
    print("Performing documentation review...")
    doc_review = review_code_documentation(sample_code)
    if doc_review:
        print(f"Documentation Rating: {doc_review.rating}/10")
        print("Documentation Issues:")
        for issue in doc_review.issues:
            print(f"- {issue}")
        print("Suggestions:")
        for suggestion in doc_review.suggestions:
            print(f"- {suggestion}")
    else:
        print("Documentation review failed to parse")
    
    # Get structured code review
    print("\nPerforming code review...")
    code_review = perform_code_review(sample_code)
    if code_review:
        print(f"Overall Code Quality: {code_review.overall_quality}/10")
        print(f"Summary: {code_review.summary}")
        print("\nFindings:")
        for finding in code_review.findings:
            print(f"- [{finding.severity.upper()}] {finding.issue_type}: {finding.description}")
            if finding.suggestion:
                print(f"  Suggestion: {finding.suggestion}")
    else:
        print("Code review failed to parse")
