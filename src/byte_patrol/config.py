from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI

# Load environment variables from .env
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek/deepseek-v3-base:free")


def get_llm(request_timeout: float = 30, max_tokens: int = 200) -> ChatOpenAI:
    """
    Factory to create a ChatOpenAI instance configured via environment.
    
    Args:
        request_timeout: Timeout for the API request in seconds
        max_tokens: Maximum number of tokens in the response
    
    Returns:
        ChatOpenAI: Configured LLM instance
    """
    return ChatOpenAI(
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        model_name=MODEL_NAME,
        request_timeout=request_timeout,
        max_tokens=max_tokens,
    )
