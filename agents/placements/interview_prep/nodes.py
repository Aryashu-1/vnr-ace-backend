import json
from typing import Dict, Any
from .state import InterviewPrepState
from .utils import load_company_data
from .services import InterviewPrepService
from .prompts import INTERVIEW_PREP_SYSTEM_PROMPT, FALLBACK_TEACHER_SYSTEM_PROMPT

def initializer_node(state: InterviewPrepState) -> Dict[str, Any]:
    """
    Loads company data into graph state.
    """
    company_name = state.get("company", "Generic")
    company_data = state.get("company_data")
    if not company_data:
        company_data = load_company_data(company_name)
    
    return {
        "company_data": company_data,
        "audit_events": state.get("audit_events", []) + [
            {"event_type": "info", "agent_name": "interview_prep", "details": {"action": "load_data", "company": company_name}}
        ]
    }

def filter_node(state: InterviewPrepState) -> Dict[str, Any]:
    """
    Filters relevant questions from company data.
    """
    user_query = state.get("user_query", "")
    topics = state.get("topics", [])
    company_data = state.get("company_data", {})
    
    filtered = InterviewPrepService.get_relevant_questions(
        company_data=company_data,
        user_query=user_query,
        topics=topics
    )
    
    return {
        "filtered_questions": filtered,
        "audit_events": state.get("audit_events", []) + [
            {"event_type": "info", "agent_name": "interview_prep", "details": {"action": "filter_questions", "count": len(filtered)}}
        ]
    }

def answer_node(state: InterviewPrepState, llm_service: Any) -> Dict[str, Any]:
    """
    Uses an LLM to generate response from filtered questions.
    """
    user_query = state.get("user_query", "")
    filtered_questions = state.get("filtered_questions", [])
    
    # Format filtered questions for the LLM
    context_str = json.dumps(filtered_questions, indent=2)
    
    
    # If no filtered questions, use the fallback teacher prompt
    system_prompt = INTERVIEW_PREP_SYSTEM_PROMPT
    if not filtered_questions:
        system_prompt = FALLBACK_TEACHER_SYSTEM_PROMPT
        user_prompt = f"User Query: '{user_query}'. Please teach the user how to prepare and answer this in an interview as a senior mentor."
    else:
        user_prompt = f"""
        User Query: '{user_query}'
        
        Relevant Interview Questions/Content:
        {context_str}
        
        Please provide an explanation, approach, code (if applicable), and interview tips.
        """
    
    response = llm_service.invoke_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    return {
        "response": response,
        "audit_events": state.get("audit_events", []) + [
            {"event_type": "info", "agent_name": "interview_prep", "details": {"action": "generate_answer"}}
        ]
    }
