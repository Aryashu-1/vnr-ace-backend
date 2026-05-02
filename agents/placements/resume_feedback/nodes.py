# agents/placements/resume_feedback/nodes.py

from __future__ import annotations
from typing import Dict, Any

import json
import google.generativeai as genai
from google.api_core import exceptions
from core.llm import get_gemini_keys
from core.config import settings

from .constants import (
    AGENT_NAME,
    ALLOWED_INTENTS,
    MAX_MEMORY_ITEMS,
    STANDARD_MESSAGES,
    COLLEGE_RESUME_RULES,
)
from .guardrails import check_access, check_language_and_exploit
from .prompts import (
    SCOPE_CLASSIFIER_PROMPT,
    INTENT_CLASSIFIER_PROMPT,
    FOLLOWUP_ANSWER_PROMPT,
    RESUME_CHAT_SYSTEM_PROMPT,
)
from .schemas import (
    ScopeClassifierOutput,
    IntentClassifierOutput,
)
from .utils import (
    make_audit_event,
    trim_memory,
    build_cache_key,
)




def access_control_node(state: Dict[str, Any]) -> Dict[str, Any]:
    allowed, reason = check_access(state.get("user_role", ""))
    state["access_granted"] = allowed

    if not allowed:
        state["rejection_reason"] = reason
        state["final_response"] = STANDARD_MESSAGES["access_denied"]
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "access_denied",
                state["user_id"],
                AGENT_NAME,
                {"role": state.get("user_role"), "query": state.get("user_query")},
            )
        )
    return state


def language_guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    safe, exploit, reason = check_language_and_exploit(state.get("user_query", ""))
    state["safe_language"] = safe
    state["exploit_detected"] = exploit

    if not safe:
        state["rejection_reason"] = reason
        state["final_response"] = STANDARD_MESSAGES["unsafe_language"]
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "unsafe_or_exploit_query",
                state["user_id"],
                AGENT_NAME,
                {"query": state.get("user_query"), "reason": reason},
            )
        )
    return state


def scope_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    query = state.get("user_query", "")

    if llm_service is None:
        q = query.lower()
        kws = ["resume", "ats", "cv", "projects", "skills", "experience"]
        label = "in_scope" if any(k in q for k in kws) else "out_of_scope"
        result = ScopeClassifierOutput(label=label, confidence=0.75, reason="Heuristic fallback")
    else:
        result = llm_service.invoke_structured(
            system_prompt=SCOPE_CLASSIFIER_PROMPT,
            user_prompt=query,
            schema=ScopeClassifierOutput,
        )

    state["in_scope"] = result.label == "in_scope"

    if not state["in_scope"]:
        state["rejection_reason"] = "out_of_scope"
        state["final_response"] = STANDARD_MESSAGES["out_of_scope"]
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "out_of_scope_query",
                state["user_id"],
                AGENT_NAME,
                {"query": query, "reason": result.reason, "confidence": result.confidence},
            )
        )
    return state


def intent_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    if llm_service is None:
        raise ValueError("intent_classifier_node requires llm_service for production use.")

    memory = trim_memory(state.get("memory", []), 10)
    user_prompt = (
        f"Conversation memory: {memory}\n"
        f"Current user query: {state.get('user_query', '')}\n"
        f"Allowed intents: {sorted(ALLOWED_INTENTS)}\n"
        f"Resume ID: {state.get('resume_id')}\n"
        f"Resume path present: {bool(state.get('resume_path'))}\n"
        f"Resume text present: {bool(state.get('resume_text'))}\n"
    )

    result: IntentClassifierOutput = llm_service.invoke_structured(
        system_prompt=INTENT_CLASSIFIER_PROMPT,
        user_prompt=user_prompt,
        schema=IntentClassifierOutput,
    )

    state["intent"] = result.intent
    state["intent_confidence"] = result.confidence
    state["clarification_needed"] = result.clarification_needed
    state["clarification_question"] = result.clarification_question

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "intent_classified",
            state["user_id"],
            AGENT_NAME,
            {
                "intent": result.intent,
                "confidence": result.confidence,
                "clarification_needed": result.clarification_needed,
            },
        )
    )
    return state


def clarification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state["final_response"] = (
        f"{STANDARD_MESSAGES['clarification_prefix']}\n"
        f"{state.get('clarification_question')}"
    )
    return state


def cache_lookup_node(state: Dict[str, Any], cache_repo: Any = None) -> Dict[str, Any]:
    cache_key = build_cache_key(
        state.get("user_id", ""),
        state.get("resume_id"),
        state.get("resume_text"),
    )
    state["cache_key"] = cache_key

    if cache_repo is None:
        state["cached_analysis_found"] = False
        return state

    cached = cache_repo.get(cache_key)
    if cached:
        state["cached_analysis_found"] = True
        state["structured_analysis"] = cached
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "resume_analysis_cache_hit",
                state["user_id"],
                AGENT_NAME,
                {"cache_key": cache_key},
            )
        )
    else:
        state["cached_analysis_found"] = False
    return state


def rag_analysis_node(state: Dict[str, Any], rag_service: Any = None, cache_repo: Any = None) -> Dict[str, Any]:
    if state.get("cached_analysis_found"):
        state["rag_executed"] = False
        return state

    resume_text = state.get("resume_text")
    resume_path = state.get("resume_path")

    if not resume_text and not resume_path:
        state["final_response"] = STANDARD_MESSAGES["no_resume"]
        return state

    if rag_service is None:
        # placeholder / mock structured output
        analysis = {
            "overall_score": 74.0,
            "summary": ["Mock resume analysis completed."],
            "strengths": ["Good project exposure", "Relevant technical stack"],
            "weaknesses": ["Experience section needs stronger impact statements"],
            "ats_issues": ["Use role-specific keywords from job descriptions"],
            "priority_fixes": ["Add quantified achievements", "Add GitHub link"],
            "section_feedback": {
                "projects": {
                    "score": 7.5,
                    "strengths": ["Relevant projects"],
                    "issues": ["Missing measurable outcomes"],
                    "suggestions": ["Add metrics"],
                    "example_rewrites": ["Increased X by Y%"]
                }
            }
        }
    else:
        analysis = rag_service.analyze_resume(
            resume_text=resume_text,
            resume_path=resume_path,
        )

    state["structured_analysis"] = analysis
    state["rag_executed"] = True

    if cache_repo is not None and state.get("cache_key"):
        cache_repo.put(
            cache_key=state["cache_key"],
            analysis=analysis,
            metadata={
                "user_id": state.get("user_id"),
                "resume_id": state.get("resume_id"),
            },
        )

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "resume_analyzed",
            state["user_id"],
            AGENT_NAME,
            {"used_cache": False},
        )
    )
    return state


def initial_analysis_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    analysis = state.get("structured_analysis", {})
    prefix = STANDARD_MESSAGES["cached_used"] if state.get("cached_analysis_found") else STANDARD_MESSAGES["analysis_complete"]

    # Safely handle the response which could come from the mock or the actual Gemini call
    summary_parts = analysis.get("summary", [])
    if isinstance(summary_parts, list):
        summary = "\n".join(f"- {s}" for s in summary_parts)
    else:
        summary = summary_parts

    overall_score = analysis.get("overall_score", "N/A")
    
    ats_issues = analysis.get("ats_issues", [])
    ats_issues_str = "\n".join(f"- {i}" for i in ats_issues) if ats_issues else "None"
    
    priority_fixes = analysis.get("priority_fixes", [])
    priority_fixes_str = "\n".join(f"- {f}" for f in priority_fixes) if priority_fixes else "None"

    section_feedback = analysis.get("section_feedback", {})
    section_feedback_str = ""
    for section, feedback in section_feedback.items():
        section_feedback_str += f"\n#### {section.replace('_', ' ').capitalize()}\n"
        if isinstance(feedback, dict):
            issues = feedback.get("issues", [])
            if issues:
                section_feedback_str += "**Issues:**\n" + "\n".join(f"- {i}" for i in issues) + "\n"
            suggestions = feedback.get("suggestions", [])
            if suggestions:
                section_feedback_str += "**Suggestions:**\n" + "\n".join(f"- {s}" for s in suggestions) + "\n"
            examples = feedback.get("example_rewrites", [])
            if examples:
                section_feedback_str += "**Example Rewrites:**\n" + "\n".join(f"- {e}" for e in examples) + "\n"
        elif isinstance(feedback, str):
            section_feedback_str += f"{feedback}\n"

    state["final_response"] = (
        f"{prefix}\n\n"
        f"### Resume Analysis Overview\n"
        f"**Overall Score:** {overall_score}/100\n\n"
        f"#### Summary\n{summary}\n\n"
        f"#### Priority Fixes\n{priority_fixes_str}\n\n"
        f"#### ATS Optimization\n{ats_issues_str}\n\n"
        f"### Section-by-Section Feedback\n{section_feedback_str}"
    )
    return state


def followup_answer_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    analysis = state.get("structured_analysis", {})

    if not analysis:
        state["final_response"] = "No prior resume analysis is available for follow-up."
        return state

    if llm_service is None:
        state["final_response"] = (
            f"Based on the stored analysis, here is the answer to your question:\n"
            f"{state.get('user_query')}\n\n"
            f"Relevant analysis context: {analysis}"
        )
        return state

    user_prompt = (
        f"User follow-up question: {state.get('user_query')}\n"
        f"Stored structured analysis: {analysis}"
    )

    answer = llm_service.invoke_text(
        system_prompt=FOLLOWUP_ANSWER_PROMPT,
        user_prompt=user_prompt,
    )
    state["final_response"] = answer
    return state


def memory_update_node(state: Dict[str, Any]) -> Dict[str, Any]:
    memory = state.get("memory", [])
    memory.append({
        "user_query": state.get("user_query"),
        "intent": state.get("intent"),
        "cache_hit": state.get("cached_analysis_found", False),
        "rag_executed": state.get("rag_executed", False),
    })
    state["memory"] = trim_memory(memory, MAX_MEMORY_ITEMS)
    return state


def persist_audit_logs_node(state: Dict[str, Any], audit_repo: Any = None) -> Dict[str, Any]:
    if audit_repo is not None:
        audit_repo.persist_events(state.get("audit_events", []))
    return state


# ----------------------------------------------------------
# Resume Chat Node  (contextual Q&A grounded on analysis)
# ----------------------------------------------------------

def resume_chat_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stateless Gemini-powered node for multi-turn chat about a resume analysis.

    Required state keys:
        structured_analysis  – dict produced by /resume/analyze
        user_query           – the user's current question
        conversation_history – list of {"role": "user"|"model", "parts": [str]}
                               (Gemini native format; pass [] for first turn)
    Writes:
        final_response       – the model's reply text
        conversation_history – updated list with new user + model turns appended
    """
    analysis = state.get("structured_analysis")
    user_query = state.get("user_query", "").strip()

    if not analysis:
        state["final_response"] = (
            "No resume analysis is available yet. "
            "Please upload and analyze your resume first."
        )
        return state

    if not user_query:
        state["final_response"] = "Please ask a question about your resume."
        return state

    # Build system prompt with analysis embedded
    analysis_json = json.dumps(analysis, indent=2)
    system_prompt = (
        RESUME_CHAT_SYSTEM_PROMPT
        + f"\n\n--- COLLEGE SPECIFIC RULES ---\n{COLLEGE_RESUME_RULES}\n--- END OF RULES ---"
        + f"\n\n--- RESUME ANALYSIS ---\n{analysis_json}\n--- END OF ANALYSIS ---"
    )

    # Restore or initialise Gemini chat history
    history = state.get("conversation_history", [])

    keys = get_gemini_keys()
    if not keys:
        state["final_response"] = "System Error: Gemini API keys are not configured."
        return state

    reply_text = ""
    last_error = None
    for key in keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=system_prompt,
            )
            chat = model.start_chat(history=history)

            response = chat.send_message(
                user_query,
                generation_config=genai.types.GenerationConfig(temperature=0.3),
            )
            reply_text = response.text
            break # Success
        except exceptions.ResourceExhausted as e:
            print(f"Gemini quota exceeded for a key in chat node. Trying next key... Error: {e}")
            last_error = e
            continue
        except Exception as e:
            print(f"Gemini chat failed: {e}")
            last_error = e
            continue
    
    if not reply_text:
        state["final_response"] = "Error: Could not get a response from Gemini after trying multiple keys."
        return state

    # Append the new turn to history so the caller can persist it
    updated_history = list(history) + [
        {"role": "user", "parts": [user_query]},
        {"role": "model", "parts": [reply_text]},
    ]

    state["final_response"] = reply_text
    state["conversation_history"] = updated_history
    return state