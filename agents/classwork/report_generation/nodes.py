# agents/classwork/report_generation/nodes.py

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .constants import (
    AGENT_NAME,
    ALLOWED_EXPORT_FORMATS,
    ALLOWED_REPORT_TYPES,
    DATASET_ALLOWED_COLUMNS,
    DATASET_REGISTRY,
    DEFAULT_EXPORT_FORMAT,
    DEFAULT_PREVIEW_LIMIT,
    STANDARD_MESSAGES,
)
from .guardrails import check_access, check_language_and_exploit
from .prompts import PLANNER_SYSTEM_PROMPT, SCOPE_CLASSIFIER_PROMPT
from .schemas import PlannerOutput, ScopeClassifierOutput
from .utils import (
    apply_dataframe_filters,
    dataframe_summary,
    export_dataframe,
    generate_preview_message,
    join_students_with_attendance,
    join_students_with_marks,
    limit_preview_rows,
    make_audit_event,
    validate_filter_columns_against_datasets,
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
                {
                    "role": state.get("user_role"),
                    "query": state.get("user_query"),
                },
            )
        )
    return state


def scope_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    query = state.get("user_query", "")

    if llm_service is None:
        # fallback heuristic if service not injected
        q = query.lower()
        in_scope_keywords = [
            "report", "student list", "attendance", "marks", "performance",
            "defaulter", "section summary", "subject summary", "semester"
        ]
        label = "in_scope" if any(k in q for k in in_scope_keywords) else "out_of_scope"
        confidence = 0.70 if label == "in_scope" else 0.85
        reason = "Heuristic fallback classifier used."
        result = ScopeClassifierOutput(label=label, confidence=confidence, reason=reason)
    else:
        result = llm_service.invoke_structured(
            system_prompt=SCOPE_CLASSIFIER_PROMPT,
            user_prompt=query,
            schema=ScopeClassifierOutput,
        )

    state["scope_classifier_label"] = result.label
    state["scope_confidence"] = result.confidence
    state["in_scope"] = result.label == "in_scope"

    if not state["in_scope"]:
        state["rejection_reason"] = "out_of_scope"
        state["final_response"] = STANDARD_MESSAGES["out_of_scope"]
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "out_of_scope_query",
                state["user_id"],
                AGENT_NAME,
                {
                    "query": query,
                    "confidence": result.confidence,
                    "reason": result.reason,
                },
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
                {
                    "query": state.get("user_query"),
                    "reason": reason,
                },
            )
        )
    return state


def planner_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    if llm_service is None:
        raise ValueError("planner_node requires llm_service for production use.")

    user_prompt = (
        f"User query: {state.get('user_query', '')}\n"
        f"Conversation history: {state.get('messages', [])}\n"
        f"Allowed report types: {sorted(ALLOWED_REPORT_TYPES)}\n"
        f"Allowed datasets: {sorted(DATASET_REGISTRY.keys())}\n"
        f"Allowed export formats: {sorted(ALLOWED_EXPORT_FORMATS)}\n"
        f"Known dataset columns: { {k: sorted(v) for k, v in DATASET_ALLOWED_COLUMNS.items()} }\n"
    )

    result: PlannerOutput = llm_service.invoke_structured(
        system_prompt=PLANNER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=PlannerOutput,
    )

    export_format = result.export_format or DEFAULT_EXPORT_FORMAT
    if export_format not in ALLOWED_EXPORT_FORMATS:
        export_format = DEFAULT_EXPORT_FORMAT

    state["interpreted_intent"] = result.interpreted_intent
    state["report_type"] = result.report_type
    state["target_filters"] = result.filters
    state["required_datasets"] = result.required_datasets
    state["export_format"] = export_format
    state["clarification_needed"] = result.clarification_needed
    state["clarification_question"] = result.clarification_question
    state["plan"] = result.model_dump()

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "report_plan_created",
            state["user_id"],
            AGENT_NAME,
            {
                "report_type": state["report_type"],
                "filters": state["target_filters"],
                "datasets": state["required_datasets"],
                "clarification_needed": state["clarification_needed"],
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


async def load_data_node(state: Dict[str, Any], data_repo: Any = None) -> Dict[str, Any]:
    required = state.get("required_datasets", [])
    if data_repo is None:
        raise ValueError("load_data_node requires data_repo for production use.")
    state["loaded_data"] = await data_repo.load_datasets(required)
    return state


def strict_column_validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    filters = state.get("target_filters", {})
    required_datasets = state.get("required_datasets", [])

    invalid_columns = validate_filter_columns_against_datasets(
        filters=filters,
        dataset_names=required_datasets,
        dataset_allowed_columns=DATASET_ALLOWED_COLUMNS,
    )

    state["invalid_filter_columns"] = invalid_columns

    issues = state.get("validation_issues", [])
    if invalid_columns:
        issues.append(
            f"Invalid filter columns detected: {', '.join(invalid_columns)}"
        )
    if state.get("report_type") not in ALLOWED_REPORT_TYPES:
        issues.append(f"Unsupported report type: {state.get('report_type')}")

    for ds in required_datasets:
        if ds not in DATASET_REGISTRY:
            issues.append(f"Unregistered dataset requested: {ds}")

    state["validation_issues"] = issues
    return state


def analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    report_type = state["report_type"]
    filters = state.get("target_filters", {})
    loaded = state.get("loaded_data", {})

    students_df: pd.DataFrame | None = loaded.get("students")
    attendance_df: pd.DataFrame | None = loaded.get("attendance")
    marks_df: pd.DataFrame | None = loaded.get("marks")

    if students_df is None:
        raise ValueError("students dataset is required for this report agent.")

    base_students = apply_dataframe_filters(students_df, {
        k: v for k, v in filters.items() if k in students_df.columns
    })

    final_df = base_students.copy()

    if report_type in {"attendance_report", "defaulter_report", "subject_summary"}:
        if attendance_df is None:
            raise ValueError("attendance dataset required but not loaded.")
        final_df = join_students_with_attendance(base_students, attendance_df)

        remaining_filters = {
            k: v for k, v in filters.items()
            if k in final_df.columns and k not in students_df.columns
        }
        final_df = apply_dataframe_filters(final_df, remaining_filters)

        if report_type == "defaulter_report":
            if "attendance_percent" not in final_df.columns:
                raise ValueError("attendance_percent column is required for defaulter_report.")
            final_df = final_df[final_df["attendance_percent"] < 75]

    elif report_type in {"performance_report"}:
        if marks_df is None:
            raise ValueError("marks dataset required but not loaded.")
        final_df = join_students_with_marks(base_students, marks_df)

        remaining_filters = {
            k: v for k, v in filters.items()
            if k in final_df.columns and k not in students_df.columns
        }
        final_df = apply_dataframe_filters(final_df, remaining_filters)

    elif report_type in {"student_list", "section_summary"}:
        final_df = base_students

    else:
        raise ValueError(f"Unsupported report type in analysis: {report_type}")

    state["final_dataframe"] = final_df
    state["analysis_result"] = dataframe_summary(final_df)
    state["preview_result"] = {
        "preview_rows": limit_preview_rows(final_df, DEFAULT_PREVIEW_LIMIT)
    }

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "report_analyzed",
            state["user_id"],
            AGENT_NAME,
            {
                "report_type": report_type,
                "row_count": state["analysis_result"]["row_count"],
            },
        )
    )
    return state


def validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    issues = state.get("validation_issues", [])

    final_df = state.get("final_dataframe")
    preview = state.get("preview_result", {}).get("preview_rows", [])

    if final_df is None:
        issues.append("Final dataframe was not generated.")

    if "analysis_result" not in state:
        issues.append("Analysis result missing.")

    if preview is None:
        issues.append("Preview rows missing.")

    if state.get("invalid_filter_columns"):
        issues.append("Unknown filter columns were used.")

    state["validation_issues"] = issues
    state["validation_passed"] = len(issues) == 0

    if not state["validation_passed"]:
        state["final_response"] = (
            f"{STANDARD_MESSAGES['validation_failed']} Issues: {issues}"
        )
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "validation_failed",
                state["user_id"],
                AGENT_NAME,
                {"issues": issues},
            )
        )
    return state


def approval_pause_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state["approval_required"] = True
    state["approval_status"] = "pending"
    state["waiting_for_human"] = True

    row_count = state["analysis_result"]["row_count"]
    preview_rows = state["preview_result"]["preview_rows"]

    state["final_response"] = generate_preview_message(
        report_type=state["report_type"],
        row_count=row_count,
        preview_rows=preview_rows,
    )

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "awaiting_human_approval",
            state["user_id"],
            AGENT_NAME,
            {"report_type": state["report_type"]},
        )
    )
    return state


def human_decision_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    This node is entered only after UI resumes the graph with:
    - human_approved = True / False
    - approval_notes optional
    """
    approved = state.get("human_approved")

    if approved is True:
        state["approval_status"] = "approved"
        state["waiting_for_human"] = False
    else:
        state["approval_status"] = "rejected"
        state["waiting_for_human"] = False
        state["final_response"] = "Report generation was not approved. No final report was produced."

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "human_decision_recorded",
            state["user_id"],
            AGENT_NAME,
            {
                "approved": approved,
                "notes": state.get("approval_notes"),
            },
        )
    )
    return state


def final_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    df: pd.DataFrame = state["final_dataframe"]
    export_format = state.get("export_format", DEFAULT_EXPORT_FORMAT)

    artifact_path = export_dataframe(
        df=df,
        output_dir="artifacts/classwork_reports",
        report_type=state["report_type"],
        extension=export_format,
    )

    state["downloadable_artifact_path"] = artifact_path
    state["final_response"] = (
        f"Final report generated successfully.\n"
        f"Report type: {state['report_type']}\n"
        f"Rows found: {state['analysis_result']['row_count']}\n"
        f"Artifact: {artifact_path}"
    )

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "report_generated",
            state["user_id"],
            AGENT_NAME,
            {
                "report_type": state["report_type"],
                "artifact_path": artifact_path,
                "export_format": export_format,
            },
        )
    )
    return state


def followup_node(state: Dict[str, Any]) -> Dict[str, Any]:
    query = (state.get("user_query", "") or "").strip().lower()

    if query in {"stop", "exit", "end", "close"}:
        state["stop_requested"] = True
        state["final_response"] = "Report workflow closed. Thank you!"
        return state

    state["followup_mode"] = True
    report_type = state.get("report_type", "report")
    row_count = state.get("analysis_result", {}).get("row_count", 0)
    
    state["final_response"] = (
        f"I've generated the {report_type} with {row_count} rows. "
        "What would you like to do next? You can:\n"
        "1. Filter this data further (e.g., 'only show ECE students')\n"
        "2. Change the export format (e.g., 'export as CSV')\n"
        "3. Request a different report type entirely."
    )
    return state


def persist_audit_logs_node(state: Dict[str, Any], audit_repo: Any = None) -> Dict[str, Any]:
    if audit_repo is not None:
        audit_repo.persist_events(state.get("audit_events", []))
    return state
