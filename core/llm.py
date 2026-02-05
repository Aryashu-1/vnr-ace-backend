# core/llm.py

from langchain_groq import ChatGroq
from core.config import settings

# Initialize Groq LLM
groq_llm = ChatGroq(
    model="llama-3.1-8b-instant",    # Best model on Groq
    groq_api_key=settings.GROQ_API_KEY,
    temperature=0.2,
)

async def call_llm(prompt: str):
    """
    Generic helper for all LangGraph agents.
    """
    response = groq_llm.invoke(prompt)
    return response.content
