from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from .env
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")


def get_llm(request_timeout: float = 30, max_tokens: int = 200) -> ChatOpenAI:
    """
    Factory to create a ChatOpenAI instance configured via environment.
    
    Args:
        request_timeout: Timeout for the API request in seconds
        max_tokens: Maximum number of tokens in the response
    
    Returns:
        ChatOpenAI: Configured LLM instance
    """
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
    llm = ChatGoogleGenerativeAI(
        google_api_key=GOOGLE_API_KEY,
        model="gemini-2.0-flash"
    )
    return llm
