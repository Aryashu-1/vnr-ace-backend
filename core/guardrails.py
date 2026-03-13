from core.llm import call_llm

async def check_input_guardrail(query: str) -> bool:
    """
    Checks if the input query contains abusive, toxic, or offensive language.
    Returns True if the input is SAFE to process.
    Returns False if the input is UNSAFE (abusive/toxic).
    """
    prompt = f"""You are a strict safety guardrail for a university chatbot system.
Your task is to analyze the following user input and determine if it contains any abusive, toxic, highly offensive, or hateful language.

User Input: "{query}"

If the input is safe, polite, or just a normal question (even if it's frustrated but not abusive), respond exactly with the word "SAFE".
If the input contains abusive, toxic, highly offensive, or hateful language, respond exactly with the word "UNSAFE".

Response:"""
    try:
        response = await call_llm(prompt)
        response_clean = response.strip().upper()
        if "UNSAFE" in response_clean:
            return False
        return True
    except Exception as e:
        print(f"Error in input guardrail: {e}")
        # Default to True on error to not block legitimate requests
        return True

async def check_output_guardrail(response: str, query: str) -> bool:
    """
    Checks if the generated response contains hallucinations, confidential information leakage, or abusive content.
    Returns True if the output is SAFE to show to the user.
    Returns False if the output is UNSAFE.
    """
    prompt = f"""You are a strict safety guardrail for a university chatbot system.
Your task is to analyze the generated response to a user's query and determine if it is safe to display.

User Query: "{query}"
Generated Response: "{response}"

Criteria for UNSAFE:
1. Contains abusive, toxic, or highly offensive language.
2. Contains highly sensitive confidential information (e.g. passwords, SSNs, personal contact details that should not be public).
3. Explicitly states dangerous or illegal instructions.

If the response is safe, respond exactly with the word "SAFE".
If the response violates any of the above criteria or seems like a severe hallucination that shouldn't be shown, respond exactly with the word "UNSAFE".

Response:"""
    try:
        llm_response = await call_llm(prompt)
        response_clean = llm_response.strip().upper()
        if "UNSAFE" in response_clean:
            return False
        return True
    except Exception as e:
        print(f"Error in output guardrail: {e}")
        return True
