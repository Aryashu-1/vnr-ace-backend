from core.llm import call_llm

async def faq_agent(message: str):
    prompt = f"""
    You are the VNR-ACE Admissions FAQ Assistant.
    User question: {message}
    Provide a clear and helpful answer.
    """

    answer = await call_llm(prompt)
    return {"reply": answer}
