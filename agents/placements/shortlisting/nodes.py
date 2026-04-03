from .constants import *
from .prompts import *
from .schemas import IntentOutput
from .utils import make_event


def access_node(state):
    # Support both "user_role" (agent-specific) and "role" (unified router)
    role = state.get("user_role") or state.get("role")
    if role not in ALLOWED_ROLES:
        state["final_response"] = STANDARD_MESSAGES["access_denied"]
        return state
    return state


def intent_node(state, llm):
    result: IntentOutput = llm.invoke_structured(
        INTENT_PROMPT,
        state["user_query"],
        IntentOutput
    )
    state["intent"] = result.intent
    state["clarification_needed"] = result.clarification_needed
    state["clarification_question"] = result.clarification_question
    return state


def clarification_node(state):
    state["final_response"] = state["clarification_question"]
    return state


def rag_shortlisting_node(state, rag_service=None):
    """
    RAG-based shortlisting using FAISS.
    """
    if not state.get("jd_text"):
        # Try to use user_query if jd_text is missing
        jd_text = state.get("user_query")
        if not jd_text:
            state["final_response"] = STANDARD_MESSAGES["no_jd"]
            return state
        state["jd_text"] = jd_text

    if not rag_service:
        from .services import ShortlistingService
        rag_service = ShortlistingService()

    try:
        # JD-based shortlisting without DB filtering for the agent node (as per user request)
        candidates = rag_service.shortlist(
            jd_text=state["jd_text"], 
            top_k=state.get("no_of_students", 5)
        )
        
        if candidates:
            import asyncio
            # Since node is sync, we run the async explain_matches
            candidates = asyncio.run(rag_service.explain_matches(state["jd_text"], candidates))
        
        state["shortlisted_candidates"] = candidates
        state["rag_executed"] = True
        return state
    except Exception as e:
        state["final_response"] = f"Error during shortlisting: {str(e)}"
        return state


def response_node(state):
    candidates = state.get("shortlisted_candidates", [])

    if not candidates:
        state["final_response"] = STANDARD_MESSAGES["no_candidates"]
        return state

    state["final_response"] = f"Top Candidates:\n{candidates}"
    return state