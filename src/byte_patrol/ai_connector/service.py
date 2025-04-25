"""Connect to AI service API (e.g., OpenAI)."""

import json
from typing import Type, Any

from src.byte_patrol.config import get_llm
from langchain.schema import HumanMessage
from pydantic import BaseModel

def pydantic_to_function_schema(model_class: Type[BaseModel]) -> dict:
    """
    Convert a Pydantic model to a function schema for LLM function calling.
    
    Args:
        model_class: The Pydantic model class to convert
        
    Returns:
        dict: Function schema compatible with LLM function calling
    """
    schema = model_class.schema()
    properties = {}
    required = []
    
    for field_name, field_schema in schema.get("properties", {}).items():
        properties[field_name] = {
            "type": field_schema.get("type", "string"),
            "description": field_schema.get("description", "")
        }
        
        # Handle array types
        if field_schema.get("type") == "array" and "items" in field_schema:
            properties[field_name]["items"] = field_schema["items"]
        
        # Add field to required list if it's required
        if field_name in schema.get("required", []):
            required.append(field_name)
    
    return {
        "name": model_class.__name__,
        "description": schema.get("description", f"Generate a {model_class.__name__}"),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }

def get_structured_output(prompt: str, model_class: Type[BaseModel], **llm_kwargs) -> BaseModel:
    """
    Send a prompt to the AI service and return a structured response using function calling.
    
    Args:
        prompt: The prompt to send to the LLM
        model_class: The Pydantic model class to use for structuring the output
        **llm_kwargs: Additional keyword arguments to pass to the LLM
        
    Returns:
        BaseModel: An instance of the provided model_class with the structured response
    """
    function_schema = pydantic_to_function_schema(model_class)
    
    # Get default LLM kwargs and update with provided kwargs
    default_kwargs = {"request_timeout": 30, "max_tokens": 1000}
    default_kwargs.update(llm_kwargs)
    
    llm = get_llm(**default_kwargs)
    
    # Use function calling
    response = llm.invoke(
        [{"role": "user", "content": prompt}],
        functions=[function_schema],
        function_call={"name": model_class.__name__}
    )

    # Parse the function call arguments
    function_args = response.additional_kwargs.get("function_call", {}).get("arguments", "{}")
    
    # Convert to Pydantic model
    return model_class.parse_raw(function_args)
