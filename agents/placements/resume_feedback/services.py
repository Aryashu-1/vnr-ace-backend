# agents/placements/resume_feedback/services.py

from __future__ import annotations
from typing import Any, Dict, List, Optional
import pdfplumber
from docx import Document
from pathlib import Path
import json
import re
import os
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel
from .constants import COLLEGE_RESUME_RULES
load_dotenv()

class SectionFeedback(BaseModel):
    issues: List[str]
    suggestions: List[str]
    example_rewrites: List[str]

class ResumeAnalysis(BaseModel):
    overall_score: int
    summary: List[str]
    section_feedback: Dict[str, SectionFeedback]
    ats_issues: List[str]
    priority_fixes: List[str]

class ResumeAdvisor:
    def __init__(self, name: str = "Assistant", email: str = "assistant@vnr.edu.in"):
        self.name = name
        self.email = email
    
    def _call_gemini(self, messages: list) -> str:
        """
        Calls Gemini API with the provided messages.
        """
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        MODEL_NAME = "models/gemini-2.5-flash"

        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=messages[0]["content"]
        )

        chat = model.start_chat(history=[])

        response = chat.send_message(
            messages[1]["content"],
            generation_config=genai.types.GenerationConfig(
                temperature=0.2
            )
        )

        return response.text

    def _extract_text(self, file_path: str) -> str:
        path = Path(file_path)

        if path.suffix.lower() == ".pdf":
            return self._extract_pdf(path)
        elif path.suffix.lower() == ".docx":
            return self._extract_docx(path)
        elif path.suffix.lower() == ".txt":
            return path.read_text(encoding="utf-8")
        else:
            raise ValueError("Unsupported file format")

    def _extract_pdf(self, path: Path) -> str:
        text = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or "")
        return "\n".join(text)

    def _extract_docx(self, path: Path) -> str:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    
    def _normalize_resume(self, text: str) -> str:
        text = re.sub(r"\r", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[•●▪]", "-", text)
        return text.strip()

    def _analyze_resume(
            self,
            resume_text: str,
            target_role: str = "General",
            experience_level: str = "Unknown"
        ) -> ResumeAnalysis:

        SYSTEM_PROMPT = """
        You are an expert resume reviewer, recruiter, and ATS optimization specialist.
        You are critical, specific, and practical.
        """
        user_prompt = f"""
        Analyze the resume below.

        Target Role: {target_role}
        Experience Level: {experience_level}

        MANDATORY RULES:
        {COLLEGE_RESUME_RULES}

        Your job:
        - Analyze for professional quality AND strict compliance with Mandatory Rules.
        - Penalize if rules are broken (e.g. multi-page for freshers, missing contacts).
        - Suggest specific, actionable fixes for each rule violation.

        Return STRICT JSON matching this schema:

        {{
        "overall_score": number (0-100),
        "summary": [string],
        "section_feedback": {{
            "experience": {{
            "issues": [string],
            "suggestions": [string],
            "example_rewrites": [string]
            }}
        }},
        "ats_issues": [string],
        "priority_fixes": [string]
        }}

        Be specific. Provide concrete rewrite examples.

        Resume:
        \"\"\"
        {resume_text}
        \"\"\"
        """

        response = self._call_gemini([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ])

        response = response.replace("```json", " ").strip()
        response = response.replace("```", " ").strip()

        parsed = json.loads(response)
        return ResumeAnalysis(**parsed)

    def analyze(self, resume_path: str = None, resume_text: str = None) -> ResumeAnalysis:
        if resume_path:
            raw_text = self._extract_text(resume_path)
            clean_text = self._normalize_resume(raw_text)
        elif resume_text:
            clean_text = self._normalize_resume(resume_text)
        else:
            raise ValueError("Either resume_path or resume_text must be provided")

        return self._analyze_resume(
            resume_text=clean_text,
            target_role="Software Engineer", 
            experience_level="Entry-Level" 
        )


class LLMService:
    def __init__(self, llm: Any):
        self.llm = llm

    def invoke_structured(self, system_prompt: str, user_prompt: str, schema: Any) -> Any:
        raise NotImplementedError

    def invoke_text(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class ResumeAnalysisCacheRepository:
    """
    Back by DB / Redis / document store.
    """

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def put(self, cache_key: str, analysis: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        raise NotImplementedError


class ResumeRAGService:
    """
    Implementation of Resume feedback service using ResumeAdvisor logic.
    """
    def __init__(self):
        self.advisor = ResumeAdvisor()

    def analyze_resume(self, resume_text: str | None = None, resume_path: str | None = None) -> Dict[str, Any]:
        """
        Return structured analysis dict compatible with StructuredResumeAnalysis.
        """
        if resume_path:
            text = self.advisor._extract_text(resume_path)
        else:
            text = resume_text

        analysis = self.advisor.analyze(resume_path=resume_path, resume_text=resume_text)
        result = analysis.model_dump()
        result["resume_text"] = text
        return result


class AuditLogRepository:
    def __init__(self, db_client: Any):
        self.db_client = db_client

    def persist_events(self, events: List[Dict[str, Any]]) -> None:
        if not events:
            return
        pass