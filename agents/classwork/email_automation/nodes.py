# agents/classwork/mail_automation/nodes.py

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


def intent_node(state, llm):
    result: IntentOutput = llm.invoke_structured(
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


def search_node(state, sql_repo, llm):
    if state.get("clarification_needed"):
        return state

    # 1. Generate Query
    search_input = f"Search Criteria: {state.get('search_criteria')}\nEntities: {state.get('interpreted_entities')}"
    query_result: SearchOutput = llm.invoke_structured(
        SEARCH_QUERY_PROMPT,
        search_input,
        SearchOutput
    )

    # 2. Execute
    rows = asyncio.run(sql_repo.execute_read_only(
        query_result.sql_query,
        query_result.sql_params
    ))

    # 3. Collect emails
    emails = [row["email"] for row in rows if "email" in row]
    state["recipients"] = emails
    return state


def clarification_node(state):
    state["final_response"] = state["clarification_question"]
    return state


def draft_node(state, llm):
    result: EmailDraftOutput = llm.invoke_structured(
        EMAIL_DRAFT_PROMPT,
        state["user_query"],
        EmailDraftOutput
    )
    state["recipients"] = result.recipients
    state["subject"] = result.subject
    state["body"] = result.body
    return state


def approval_node(state):
    state["approval_required"] = True
    state["waiting_for_human"] = True
    state["final_response"] = f"""
Draft Email:

To: {state['recipients']}
Subject: {state['subject']}

{state['body']}

Approve to send.
"""
    return state


def decision_node(state):
    if state.get("human_approved"):
        state["approval_status"] = "approved"
    else:
        state["approval_status"] = "rejected"
        state["final_response"] = STANDARD_MESSAGES["not_approved"]
    return state


def send_node(state, email_service):
    email_service.send_email(
        state["recipients"],
        state["subject"],
        state["body"]
    )
    state["email_sent"] = True
    state["final_response"] = STANDARD_MESSAGES["sent_success"]
    return state


def audit_node(state, repo):
    repo.persist(state.get("audit_events", []))
    return state