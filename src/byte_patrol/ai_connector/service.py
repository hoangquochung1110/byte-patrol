"""Connect to AI service API (e.g., OpenAI)."""

from byte_patrol.config import get_llm
from langchain.schema import HumanMessage

def send_prompt(prompt: str) -> dict:
    """
    Send a prompt to the AI service and return the response.
    """
    llm = get_llm()
    ai_message = llm([HumanMessage(content=prompt)])
    return {"content": ai_message.content}
