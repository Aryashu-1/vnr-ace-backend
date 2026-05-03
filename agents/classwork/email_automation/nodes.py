# agents/classwork/mail_automation/nodes.py
import asyncio
from .constants import *
from .guardrails import check_access, check_language
from .utils import make_event
from .prompts import *
from .schemas import IntentOutput, EmailDraftOutput, SearchOutput


def access_node(state):
    ok, _ = check_access(state["user_role"])
    state["access_granted"] = ok
    if not ok:
        state["final_response"] = STANDARD_MESSAGES["access_denied"]
    return state


def language_node(state):
    safe, exploit, _ = check_language(state["user_query"])
    state["safe_language"] = safe
    if not safe:
        state["final_response"] = STANDARD_MESSAGES["unsafe_language"]
    return state


async def intent_node(state, llm):
    result: IntentOutput = await llm.ainvoke_structured(
        INTENT_PROMPT,
        state["user_query"],
        IntentOutput
    )
    state["intent"] = result.intent
    state["interpreted_entities"] = result.interpreted_entities
    state["search_criteria"] = result.search_criteria
    state["clarification_needed"] = result.clarification_needed
    state["clarification_question"] = result.clarification_question
    return state


async def search_node(state, sql_repo, llm):
    if state.get("clarification_needed"):
        return state

    # 1. Generate Query
    search_input = f"Search Criteria: {state.get('search_criteria')}\nEntities: {state.get('interpreted_entities')}"
    query_result: SearchOutput = await llm.ainvoke_structured(
        SEARCH_QUERY_PROMPT,
        search_input,
        SearchOutput
    )

    # 2. Execute
    try:
        rows = await sql_repo.execute_read_only(query_result.sql_query, query_result.sql_params)
        emails = [row["email"] for row in rows if "email" in row]
        state["recipients"] = emails
    except Exception as e:
        print(f"SQL execution error: {e}")
        state["recipients"] = []
    
    return state


def clarification_node(state):
    state["final_response"] = state["clarification_question"]
    return state


async def draft_node(state, llm):
    # Context if we found recipients
    context = ""
    recipients = state.get("recipients", [])
    if recipients:
        context = f"Found {len(recipients)} recipients. "
        if len(recipients) < 10:
             context += f"Emails: {', '.join(recipients)}"
        else:
             context += f"Examples: {', '.join(recipients[:5])}..."

    result: EmailDraftOutput = await llm.ainvoke_structured(
        EMAIL_DRAFT_PROMPT,
        f"User Query: {state['user_query']}\nContext: {context}",
        EmailDraftOutput
    )
    
    # If LLM didn't return recipients but we found them in search, merge them
    if not result.recipients and state.get("recipients"):
        result.recipients = state["recipients"]

    state["recipients"] = result.recipients
    state["subject"] = result.subject
    state["body"] = result.body
    
    recipient_count = len(state.get('recipients', []))
    state["final_response"] = f"I've drafted the email for {recipient_count} recipients. Please review the details below."
    return state


def approval_node(state):
    state["approval_required"] = True
    return state


def decision_node(state):
    if state.get("human_approved"):
        state["approval_status"] = "approved"
    else:
        state["approval_status"] = "rejected"
        state["final_response"] = STANDARD_MESSAGES["not_approved"]
    return state


async def send_node(state, email_service):
    if not state.get("recipients"):
        state["final_response"] = "No recipients found to send to."
        return state

    success = email_service.send_email(
        state["recipients"],
        state["subject"],
        state["body"]
    )
    if success:
        state["email_sent"] = True
        state["final_response"] = STANDARD_MESSAGES["sent_success"]
        # Clear state after successful send to allow new drafts in the same thread
        state["human_approved"] = False
        state["approval_status"] = None
        state["recipients"] = []
        state["subject"] = None
        state["body"] = None
    else:
        state["final_response"] = "Failed to send email. Please check configuration."
    return state


def audit_node(state, repo):
    # repo.persist(state.get("audit_events", []))
    pass
    return state