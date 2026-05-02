import json
from typing import Dict, Any, List
from .state import InterviewPrepState
from .services import InterviewPrepRepository
from .prompts import INTERVIEW_PREP_SYSTEM_PROMPT, FALLBACK_TEACHER_SYSTEM_PROMPT

from core.db import AsyncSessionLocal

async def initializer_node(state: InterviewPrepState) -> Dict[str, Any]:
    """
    Initializes metadata and basic company info from DB.
    """
    company_name = state.get("company", "Generic")
    
    async with AsyncSessionLocal() as session:
        repo = InterviewPrepRepository(session)
        experiences = await repo.get_company_experiences(company_name)
    
    return {
        "company_data": {"experiences": experiences},
        "audit_events": state.get("audit_events", []) + [
            {"event_type": "info", "agent_name": "interview_prep", "details": {"action": "load_experiences", "company": company_name}}
        ]
    }

async def filter_node(state: InterviewPrepState) -> Dict[str, Any]:
    """
    Fetches relevant questions directly from DB based on query/topics.
    """
    user_query = state.get("user_query", "")
    topics = state.get("topics", [])
    company_name = state.get("company", "Generic")
    
    async with AsyncSessionLocal() as session:
        repo = InterviewPrepRepository(session)
        filtered = await repo.get_questions_by_company(
            company_name=company_name,
            query=user_query,
            topics=topics
        )
    
    return {
        "filtered_questions": filtered,
        "audit_events": state.get("audit_events", []) + [
            {"event_type": "info", "agent_name": "interview_prep", "details": {"action": "fetch_db_questions", "count": len(filtered)}}
        ]
    }

async def answer_node(state: InterviewPrepState, llm_service: Any) -> Dict[str, Any]:
    """
    Uses an LLM to generate response from filtered questions.
    """
    user_query = state.get("user_query", "")
    filtered_questions = state.get("filtered_questions", [])
    company_name = state.get("company", "Generic")
    
    # Format filtered questions for the LLM
    context_str = json.dumps(filtered_questions, indent=2)
    
    system_prompt = INTERVIEW_PREP_SYSTEM_PROMPT
    if not filtered_questions:
        system_prompt = FALLBACK_TEACHER_SYSTEM_PROMPT
        user_prompt = f"User Query: '{user_query}' for company '{company_name}'. Please teach the user how to prepare and answer this in an interview as a senior mentor."
    else:
        user_prompt = f"""
        Company: {company_name}
        User Query: '{user_query}'
        
        Relevant Interview Questions/Content from our Database:
        {context_str}
        
        Please provide an explanation, approach, code (if applicable), and interview tips based on these real experiences.
        """
    
    response = await llm_service.ainvoke_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    return {
        "response": response,
        "audit_events": state.get("audit_events", []) + [
            {"event_type": "info", "agent_name": "interview_prep", "details": {"action": "generate_answer"}}
        ]
    }
