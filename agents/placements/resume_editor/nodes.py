from __future__ import annotations

from typing import Any, Dict

from .utils import ALLOWED_INTENTS, ALLOWED_SECTIONS, detect_section_from_text, make_audit_event, normalize_resume_json

AGENT_NAME = "placements_resume_editor"


def access_control_node(state: Dict[str, Any]) -> Dict[str, Any]:
    allowed_roles = {"student", "placement_coordinator", "tpo", "admin"}
    state["access_granted"] = state.get("user_role") in allowed_roles
    if not state["access_granted"]:
        state["final_response"] = "You are not allowed to edit resumes."
    return state


def language_guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    query = (state.get("user_query") or "").lower()
    blocked = any(token in query for token in ["fake experience", "lie on", "invent", "fabricate", "false claim"])
    state["safe_language"] = not blocked
    state["exploit_detected"] = blocked
    if blocked:
        state["final_response"] = "I can't help fabricate or falsify resume content."
    return state


async def intent_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    requested = state.get("requested_action")
    if requested in ALLOWED_INTENTS:
        state["intent"] = requested
        state["intent_confidence"] = 0.98
    else:
        q = (state.get("user_query") or "").lower()
        if "reanaly" in q:
            intent = "reanalyze_resume"
        elif "apply" in q and "suggest" in q:
            intent = "apply_suggestion"
        elif "regenerate" in q or "bullet" in q:
            intent = "regenerate_bullets"
        elif "improve" in q:
            intent = "improve_section"
        else:
            intent = "edit_section"
        state["intent"] = intent
        state["intent_confidence"] = 0.7

    state.setdefault("audit_events", []).append(
        make_audit_event("resume_editor_intent", state.get("user_id"), AGENT_NAME, {"intent": state.get("intent")})
    )
    return state


async def section_selector_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    section = state.get("section") or detect_section_from_text(state.get("user_query", ""))
    if state.get("intent") == "reanalyze_resume":
        state["selected_section"] = None
        return state

    if section not in ALLOWED_SECTIONS:
        section = "projects"
    state["selected_section"] = section
    return state


async def edit_or_generate_node(state: Dict[str, Any], editor_service: Any = None) -> Dict[str, Any]:
    db = state.get("db_session")
    if editor_service is None or db is None:
        raise ValueError("editor_service and db_session are required.")

    resume = await editor_service.fetch_resume(db, state["resume_id"])
    current_content = normalize_resume_json(resume.structured_json)
    state["resume_record"] = {
        "id": str(resume.id),
        "structured_json": current_content,
        "current_version_id": resume.current_version_id,
    }
    state["current_content"] = current_content

    intent = state.get("intent")
    section = state.get("selected_section")
    subsection_index = state.get("subsection_index")

    if intent == "reanalyze_resume":
        return state

    if intent == "edit_section":
        version = await editor_service.manual_edit(
            db,
            resume=resume,
            section=section,
            payload=state.get("payload"),
            subsection_index=subsection_index,
            change_summary=state.get("change_summary") or f"Manual edit to {section}",
        )
    elif intent in {"improve_section", "regenerate_bullets"}:
        version = await editor_service.improve_section(
            db,
            resume=resume,
            section=section,
            subsection_index=subsection_index,
            user_instruction=state.get("user_query"),
            mode=intent,
        )
    elif intent == "apply_suggestion":
        version = await editor_service.apply_suggestion(
            db,
            resume=resume,
            section=section,
            suggestion_text=state.get("suggestion_text") or state.get("user_query") or "",
            subsection_index=subsection_index,
        )
    else:
        raise ValueError(f"Unsupported resume editor intent: {intent}")

    state["saved_version"] = {
        "id": version.id,
        "version_number": version.version_number,
        "change_summary": version.change_summary,
        "created_at": version.created_at,
    }
    state["updated_content"] = version.content
    return state


def validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    issues = []
    if state.get("intent") != "reanalyze_resume" and not state.get("updated_content"):
        issues.append("No updated content was produced.")
    if state.get("intent") != "reanalyze_resume" and state.get("selected_section") not in ALLOWED_SECTIONS:
        issues.append("Unsupported section selected.")
    state["validation_issues"] = issues
    state["validation_passed"] = not issues
    if issues:
        state["final_response"] = f"Resume edit could not be saved: {issues}"
    return state


async def version_save_node(state: Dict[str, Any], editor_service: Any = None) -> Dict[str, Any]:
    db = state.get("db_session")
    if editor_service is None or db is None:
        raise ValueError("editor_service and db_session are required.")
    await editor_service.commit(db)
    return state


async def optional_reanalysis_node(state: Dict[str, Any], editor_service: Any = None) -> Dict[str, Any]:
    db = state.get("db_session")
    if editor_service is None or db is None:
        raise ValueError("editor_service and db_session are required.")

    if state.get("intent") == "reanalyze_resume" or state.get("reanalyze"):
        resume = await editor_service.fetch_resume(db, state["resume_id"])
        analysis = await editor_service.reanalyze_resume(db, resume=resume)
        await editor_service.commit(db)
        state["reanalysis_result"] = analysis
    return state


async def response_node(state: Dict[str, Any], editor_service: Any = None) -> Dict[str, Any]:
    db = state.get("db_session")
    if editor_service is None or db is None:
        raise ValueError("editor_service and db_session are required.")

    detail_payload = await editor_service.build_resume_detail_payload(db, state["resume_id"])
    state["response_payload"] = {
        "resume_id": detail_payload["resume_id"],
        "intent": state.get("intent"),
        "section": state.get("selected_section"),
        "version": state.get("saved_version"),
        "analysis": state.get("reanalysis_result") or detail_payload.get("latest_analysis"),
        "structured_json": detail_payload["structured_json"],
        "versions": detail_payload["versions"],
    }

    if state.get("intent") == "reanalyze_resume":
        state["final_response"] = "Resume re-analysis completed."
    elif state.get("saved_version"):
        version = state["saved_version"]
        state["final_response"] = (
            f"Resume updated successfully. "
            f"Version {version.get('version_number')} saved for section {state.get('selected_section')}."
        )

    return state
