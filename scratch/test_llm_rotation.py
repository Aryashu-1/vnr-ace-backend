import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from unittest.mock import patch
from core.llm import RotatedGeminiLLM
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

class TestSchema(BaseModel):
    message: str
    success: bool

from core.config import settings

async def test_rotation_logic():
    print("--- LLM Rotation Logic Verification ---")
    
    # We will simulate having one BAD key and one GOOD key
    bad_key = "invalid_key_123"
    good_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not good_key:
        print("Error: No valid GEMINI_API_KEY found in environment to test with.")
        return

    print(f"Initializing Rotated Model with [BAD_KEY, GOOD_KEY] using {settings.GEMINI_MODEL}...")
    
    # Manually create the rotated model for testing
    model = RotatedGeminiLLM(
        keys=[bad_key, good_key], 
        model_name=settings.GEMINI_MODEL,
        temperature=0.2
    )
    
    print("\n1. Testing Text Generation Fallback...")
    try:
        # This will randomly try either bad or good first. 
        # If it hits bad, it MUST retry and use good.
        response = await model.ainvoke("Say 'I am resilient!'")
        print(f"Success: {response.content}")
    except Exception as e:
        print(f"Text Test Failed: {e}")

    print("\n2. Testing Structured Output Fallback...")
    try:
        structured_llm = model.with_structured_output(TestSchema)
        result = await structured_llm.ainvoke("Generate a success message.")
        print(f"Structured Success: {result}")
    except Exception as e:
        print(f"Structured Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_rotation_logic())
