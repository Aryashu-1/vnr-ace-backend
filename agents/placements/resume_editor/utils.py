from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional


RESUME_TEMPLATE: Dict[str, Any] = {
    "personal_info": {"name": "", "email": "", "phone": "", "links": []},
    "education": [],
    "skills": [],
    "projects": [],
    "experience": [],
    "achievements": [],
}


ALLOWED_SECTIONS = set(RESUME_TEMPLATE.keys())
ALLOWED_INTENTS = {
    "edit_section",
    "improve_section",
    "regenerate_bullets",
    "apply_suggestion",
    "reanalyze_resume",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_audit_event(event_type: str, user_id: str, agent_name: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "timestamp": utc_now_iso(),
        "event_type": event_type,
        "user_id": user_id,
        "agent_name": agent_name,
        "details": details or {},
    }


def normalize_resume_json(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = deepcopy(RESUME_TEMPLATE)
    if not data:
        return normalized
    for key in RESUME_TEMPLATE:
        if key in data and data[key] is not None:
            normalized[key] = data[key]
    if not isinstance(normalized["personal_info"], dict):
        normalized["personal_info"] = deepcopy(RESUME_TEMPLATE["personal_info"])
    for key in ["education", "skills", "projects", "experience", "achievements"]:
        if not isinstance(normalized[key], list):
            normalized[key] = []
    links = normalized["personal_info"].get("links")
    if not isinstance(links, list):
        normalized["personal_info"]["links"] = []
    return normalized


def detect_section_from_text(text: str) -> Optional[str]:
    q = (text or "").lower()
    mapping = {
        "personal_info": ["personal", "email", "phone", "link", "linkedin", "github", "name"],
        "education": ["education", "degree", "cgpa", "college", "institution"],
        "skills": ["skill", "technology", "tech stack"],
        "projects": ["project", "projects"],
        "experience": ["experience", "internship", "company", "role", "work"],
        "achievements": ["achievement", "award", "certification", "accomplishment"],
    }
    for section, keywords in mapping.items():
        if any(keyword in q for keyword in keywords):
            return section
    return None


def set_section_value(content: Dict[str, Any], section: str, payload: Any, subsection_index: Optional[int] = None) -> Dict[str, Any]:
    updated = normalize_resume_json(content)
    if section == "personal_info":
        if not isinstance(payload, dict):
            raise ValueError("personal_info updates must be a JSON object.")
        updated["personal_info"].update(payload)
        return updated

    section_value = updated.get(section)
    if isinstance(section_value, list):
        if subsection_index is None:
            if not isinstance(payload, list):
                raise ValueError(f"{section} updates must be a list when replacing the full section.")
            updated[section] = payload
            return updated
        if subsection_index < 0 or subsection_index >= len(section_value):
            raise ValueError(f"subsection_index {subsection_index} is out of range for {section}.")
        if isinstance(payload, dict) and isinstance(section_value[subsection_index], dict):
            merged = dict(section_value[subsection_index])
            merged.update(payload)
            section_value[subsection_index] = merged
        else:
            section_value[subsection_index] = payload
        updated[section] = section_value
        return updated

    updated[section] = payload
    return updated


def ensure_truthfulness_guard(content_before: Dict[str, Any], content_after: Dict[str, Any], section: str) -> None:
    if section not in {"projects", "experience", "achievements"}:
        return
    before_items = content_before.get(section, [])
    after_items = content_after.get(section, [])
    if isinstance(before_items, list) and isinstance(after_items, list) and len(after_items) > len(before_items) + 3:
        raise ValueError("Generated content changed too aggressively; refusing to save potential hallucinations.")


def _normalized_scalar(value: Any) -> str:
    return str(value or "").strip().lower()


def ensure_generated_content_is_grounded(
    original_fragment: Any,
    generated_fragment: Any,
    *,
    section: str,
) -> None:
    """
    Apply conservative checks so AI-assisted rewrites stay faithful to the original facts.
    """
    if section == "personal_info":
        if not isinstance(original_fragment, dict) or not isinstance(generated_fragment, dict):
            raise ValueError("AI rewrite returned an invalid personal_info structure.")
        for field in ("name", "email", "phone"):
            original_value = _normalized_scalar(original_fragment.get(field))
            generated_value = _normalized_scalar(generated_fragment.get(field))
            if original_value and generated_value and original_value != generated_value:
                raise ValueError(f"AI rewrite changed personal_info.{field}, which is not allowed.")
        return

    if isinstance(original_fragment, list) and isinstance(generated_fragment, list):
        if len(generated_fragment) != len(original_fragment):
            raise ValueError("AI rewrite changed the number of entries in the section.")

        if section == "experience":
            for before, after in zip(original_fragment, generated_fragment):
                if isinstance(before, dict) and isinstance(after, dict):
                    for field in ("company", "role", "duration"):
                        original_value = _normalized_scalar(before.get(field))
                        generated_value = _normalized_scalar(after.get(field))
                        if original_value and generated_value and original_value != generated_value:
                            raise ValueError(f"AI rewrite changed experience.{field}, which is not allowed.")

        if section == "projects":
            for before, after in zip(original_fragment, generated_fragment):
                if isinstance(before, dict) and isinstance(after, dict):
                    original_title = _normalized_scalar(before.get("title"))
                    generated_title = _normalized_scalar(after.get("title"))
                    if original_title and generated_title and original_title != generated_title:
                        raise ValueError("AI rewrite changed a project title, which is not allowed.")

        if section == "education":
            for before, after in zip(original_fragment, generated_fragment):
                if isinstance(before, dict) and isinstance(after, dict):
                    for field in ("institution", "degree", "year"):
                        original_value = _normalized_scalar(before.get(field))
                        generated_value = _normalized_scalar(after.get(field))
                        if original_value and generated_value and original_value != generated_value:
                            raise ValueError(f"AI rewrite changed education.{field}, which is not allowed.")
        return

    if isinstance(original_fragment, dict) and isinstance(generated_fragment, dict):
        for key, original_value in original_fragment.items():
            if key not in generated_fragment:
                raise ValueError(f"AI rewrite removed required field '{key}'.")
            original_text = _normalized_scalar(original_value)
            generated_text = _normalized_scalar(generated_fragment.get(key))
            if original_text and generated_text and key in {"company", "role", "title", "institution", "degree"}:
                if original_text != generated_text:
                    raise ValueError(f"AI rewrite changed '{key}', which is not allowed.")


def parse_json_object(raw_text: str) -> Any:
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)
