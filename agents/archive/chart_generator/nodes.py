# agents/placements/chart_generator/nodes.py

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import matplotlib.pyplot as plt

from .constants import (
    AGENT_NAME,
    ALLOWED_CHART_TYPES,
    ALLOWED_DIMENSIONS,
    ALLOWED_INTENTS,
    ALLOWED_METRICS,
    STANDARD_MESSAGES,
)
from .guardrails import check_access, check_language_and_exploit
from .prompts import (
    SCOPE_CLASSIFIER_PROMPT,
    INTENT_CLASSIFIER_PROMPT,
    CHART_SPEC_PROMPT,
)
from .schemas import (
    ScopeClassifierOutput,
    IntentClassifierOutput,
    ChartSpecOutput,
)
from .utils import (
    make_audit_event,
    trim_memory,
    apply_filters,
    ensure_output_dir,
    build_chart_filename,
)


def access_control_node(state: Dict[str, Any]) -> Dict[str, Any]:
    allowed, reason = check_access(state.get("user_role", ""))
    state["access_granted"] = allowed

    if not allowed:
        state["rejection_reason"] = reason
        state["final_response"] = STANDARD_MESSAGES["access_denied"]
    return state


def language_guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    safe, exploit, reason = check_language_and_exploit(state.get("user_query", ""))
    state["safe_language"] = safe
    state["exploit_detected"] = exploit

    if not safe:
        state["rejection_reason"] = reason
        state["final_response"] = STANDARD_MESSAGES["unsafe_language"]
    return state


def scope_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    query = state.get("user_query", "")

    if llm_service is None:
        q = query.lower()
        kws = ["chart", "graph", "placement", "package", "offers", "company"]
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
    return state


def intent_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    if llm_service is None:
        raise ValueError("intent_classifier_node requires llm_service for production use.")

    memory = trim_memory(state.get("memory", []), 10)
    user_prompt = (
        f"Conversation memory: {memory}\n"
        f"Current user query: {state.get('user_query', '')}\n"
        f"Allowed intents: {sorted(ALLOWED_INTENTS)}"
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
    return state


def clarification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state["final_response"] = (
        f"{STANDARD_MESSAGES['clarification_prefix']}\n"
        f"{state.get('clarification_question')}"
    )
    return state


def chart_spec_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    if llm_service is None:
        raise ValueError("chart_spec_node requires llm_service for production use.")

    user_prompt = (
        f"User query: {state.get('user_query', '')}\n"
        f"Conversation memory: {trim_memory(state.get('memory', []), 10)}\n"
        f"Allowed chart types: {sorted(ALLOWED_CHART_TYPES)}\n"
        f"Allowed metrics: {sorted(ALLOWED_METRICS)}\n"
        f"Allowed dimensions: {sorted(ALLOWED_DIMENSIONS)}\n"
    )

    result: ChartSpecOutput = llm_service.invoke_structured(
        system_prompt=CHART_SPEC_PROMPT,
        user_prompt=user_prompt,
        schema=ChartSpecOutput,
    )

    state["chart_type"] = result.chart_type
    state["metric"] = result.metric
    state["dimension"] = result.dimension
    state["filters"] = result.filters
    state["title"] = result.title
    state["chart_spec"] = result.model_dump()
    return state


def data_prep_node(state: Dict[str, Any], analytics_repo: Any = None) -> Dict[str, Any]:
    if analytics_repo is None:
        # mock dataframe for scaffold
        df = pd.DataFrame([
            {"department": "CSE", "month": "Jan", "placements_count": 12, "avg_package": 8.1, "offers_count": 15, "company": "A"},
            {"department": "CSE", "month": "Feb", "placements_count": 10, "avg_package": 7.8, "offers_count": 12, "company": "B"},
            {"department": "ECE", "month": "Jan", "placements_count": 9, "avg_package": 6.9, "offers_count": 10, "company": "A"},
            {"department": "ECE", "month": "Feb", "placements_count": 11, "avg_package": 7.2, "offers_count": 13, "company": "C"},
        ])
    else:
        df = analytics_repo.get_base_dataframe()

    df = apply_filters(df, state.get("filters", {}))

    metric = state.get("metric")
    dimension = state.get("dimension")

    if df.empty or metric not in df.columns or dimension not in df.columns:
        state["chart_rows"] = []
        return state

    grouped = df.groupby(dimension, as_index=False)[metric].sum()
    state["chart_dataframe"] = grouped
    state["chart_rows"] = grouped.to_dict(orient="records")
    return state


def chart_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    rows = state.get("chart_rows", [])
    if not rows:
        state["final_response"] = STANDARD_MESSAGES["no_data"]
        return state

    df = state["chart_dataframe"]
    chart_type = state["chart_type"]
    dimension = state["dimension"]
    metric = state["metric"]
    title = state.get("title") or f"{metric} by {dimension}"

    output_dir = ensure_output_dir("artifacts/placement_charts")
    chart_path = output_dir / build_chart_filename(chart_type)

    plt.figure(figsize=(8, 5))

    if chart_type == "bar":
        plt.bar(df[dimension], df[metric])
    elif chart_type == "line":
        plt.plot(df[dimension], df[metric])
    elif chart_type == "pie":
        plt.pie(df[metric], labels=df[dimension], autopct="%1.1f%%")
    elif chart_type == "scatter":
        plt.scatter(df[dimension], df[metric])
    elif chart_type == "histogram":
        plt.hist(df[metric])
    elif chart_type == "stacked_bar":
        plt.bar(df[dimension], df[metric])
    else:
        state["final_response"] = f"Unsupported chart type: {chart_type}"
        return state

    plt.title(title)
    plt.xlabel(dimension)
    plt.ylabel(metric)
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()

    state["chart_path"] = str(chart_path)
    state["final_response"] = (
        f"{STANDARD_MESSAGES['chart_generated']}\n"
        f"Chart type: {chart_type}\n"
        f"Metric: {metric}\n"
        f"Dimension: {dimension}\n"
        f"Artifact: {chart_path}"
    )
    return state


def chart_explanation_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    if not state.get("chart_rows"):
        state["final_response"] = STANDARD_MESSAGES["chart_not_ready"]
        return state

    if llm_service is None:
        state["final_response"] = f"Chart summary based on rows: {state['chart_rows'][:10]}"
        return state

    prompt = (
        f"User query: {state.get('user_query')}\n"
        f"Chart spec: {state.get('chart_spec')}\n"
        f"Chart rows: {state.get('chart_rows')[:20]}"
    )
    answer = llm_service.invoke_text(
        system_prompt="Explain this placement chart clearly and faithfully.",
        user_prompt=prompt,
    )
    state["final_response"] = answer
    return state


def memory_update_node(state: Dict[str, Any]) -> Dict[str, Any]:
    memory = state.get("memory", [])
    memory.append({
        "user_query": state.get("user_query"),
        "intent": state.get("intent"),
        "chart_spec": state.get("chart_spec"),
        "chart_path": state.get("chart_path"),
    })
    state["memory"] = trim_memory(memory, 20)
    return state


def persist_audit_logs_node(state: Dict[str, Any], audit_repo: Any = None) -> Dict[str, Any]:
    if audit_repo is not None:
        audit_repo.persist_events(state.get("audit_events", []))
    return state