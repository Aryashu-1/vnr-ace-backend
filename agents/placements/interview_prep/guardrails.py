from typing import List, Dict, Any

async def interview_prep_input_guardrail(user_query: str) -> bool:
    """
    Checks if the user query is safe and relevant to interview prep.
    """
    # Simple check for now
    if not user_query or len(user_query) < 2:
        return False
        
    # Placeholder for more complex NLP safety checks
    return True

async def interview_prep_output_guardrail(response: str, query: str) -> bool:
    """
    Checks if the generated response is safe and actually answers the query.
    """
    # Simple check for now
    if not response:
        return False
        
    return True
