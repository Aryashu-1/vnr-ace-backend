from __future__ import annotations

import asyncio
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import fitz
from docx import Document
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.placements.resume_feedback.services import ResumeRAGService
from core.llm import get_llm
from models.profile import Profile
from models.resume import Resume
from models.resume_analysis_cache import ResumeAnalysisCache
from models.resume_version import ResumeVersion
from models.student import Student
from .prompts import (
    IMPROVE_SECTION_SYSTEM_PROMPT,
    REGENERATE_BULLETS_SYSTEM_PROMPT,
    STRUCTURED_RESUME_PARSER_PROMPT,
)
from .utils import (
    ensure_generated_content_is_grounded,
    normalize_resume_json,
    parse_json_object,
    set_section_value,
)


class ResumeParserService:
    async def extract_text_from_upload(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return await asyncio.to_thread(self._extract_pdf_bytes, content)
        if suffix == ".docx":
            return await asyncio.to_thread(self._extract_docx_bytes, content)
        return content.decode("utf-8", errors="ignore")

    def _extract_pdf_bytes(self, content: bytes) -> str:
        doc = fitz.open(stream=content, filetype="pdf")
        return "\n".join(page.get_text() for page in doc).strip()

    def _extract_docx_bytes(self, content: bytes) -> str:
        doc = Document(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs).strip()

    async def parse_to_structured_json(self, raw_text: str) -> Dict[str, Any]:
        raw_text = raw_text or ""
        fallback = self._heuristic_parse(raw_text)
        try:
            llm = get_llm(temperature=0)
            prompt = f"{STRUCTURED_RESUME_PARSER_PROMPT}\n\nResume text:\n{raw_text[:12000]}"
            response = await llm.ainvoke(prompt)
            structured = parse_json_object(response.content)
            return normalize_resume_json(structured)
        except Exception:
            return fallback

    def _heuristic_parse(self, raw_text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        name = lines[0] if lines else ""
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", raw_text)
        phone_match = re.search(r"(\+?\d[\d\s-]{8,}\d)", raw_text)
        links = re.findall(r"https?://\S+|github\.com/\S+|linkedin\.com/\S+", raw_text, flags=re.IGNORECASE)

        skills = []
        skill_match = re.search(r"skills[:\-]?\s*(.+)", raw_text, flags=re.IGNORECASE)
        if skill_match:
            skills = [s.strip() for s in re.split(r",|\|", skill_match.group(1)) if s.strip()]

        return normalize_resume_json(
            {
                "personal_info": {
                    "name": name,
                    "email": email_match.group(0) if email_match else "",
                    "phone": phone_match.group(0) if phone_match else "",
                    "links": links[:5],
                },
                "skills": skills,
            }
        )


class VersioningService:
    async def save_version(
        self,
        db: AsyncSession,
        *,
        resume: Resume,
        content: Dict[str, Any],
        change_summary: Optional[str],
    ) -> ResumeVersion:
        current_version = await db.scalar(
            select(func.max(ResumeVersion.version_number)).where(ResumeVersion.resume_id == resume.id)
        )
        version = ResumeVersion(
            resume_id=resume.id,
            version_number=(current_version or 0) + 1,
            content=content,
            change_summary=change_summary,
        )
        db.add(version)
        await db.flush()
        resume.current_version_id = version.id
        resume.structured_json = content
        return version


class ResumeEditorService:
    def __init__(self) -> None:
        self.parser = ResumeParserService()
        self.versioning = VersioningService()
        self.rag_service = ResumeRAGService()

    async def create_resume(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[UUID],
        filename: str,
        content: bytes,
        resume_text: Optional[str] = None,
    ) -> Resume:
        raw_text = resume_text or await self.parser.extract_text_from_upload(filename, content)
        structured = await self.parser.parse_to_structured_json(raw_text)
        student_id = await self._resolve_student_id(db, user_id)
        resume = Resume(
            user_id=user_id,
            student_id=student_id,
            file_url=filename,
            raw_text=raw_text,
            extracted_text=raw_text,
            structured_json=structured,
            metadata_json={"source_filename": filename},
        )
        db.add(resume)
        await db.flush()
        await self.versioning.save_version(
            db,
            resume=resume,
            content=structured,
            change_summary="Initial resume upload and parse",
        )
        return resume

    async def fetch_resume(self, db: AsyncSession, resume_id: str | UUID) -> Resume:
        resume = await db.scalar(select(Resume).where(Resume.id == resume_id))
        if resume is None:
            raise ValueError("Resume not found.")
        return resume

    async def fetch_versions(self, db: AsyncSession, resume_id: str | UUID) -> List[ResumeVersion]:
        rows = await db.scalars(
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == resume_id)
            .order_by(desc(ResumeVersion.version_number))
        )
        return list(rows.all())

    async def fetch_latest_analysis(self, db: AsyncSession, resume_id: str | UUID) -> Optional[ResumeAnalysisCache]:
        return await db.scalar(
            select(ResumeAnalysisCache)
            .where(ResumeAnalysisCache.resume_id == resume_id)
            .order_by(desc(ResumeAnalysisCache.created_at))
            .limit(1)
        )

    async def build_resume_detail_payload(self, db: AsyncSession, resume_id: str | UUID) -> Dict[str, Any]:
        resume = await self.fetch_resume(db, resume_id)
        versions = await self.fetch_versions(db, resume_id)
        latest_analysis = await self.fetch_latest_analysis(db, resume_id)
        return {
            "resume_id": str(resume.id),
            "user_id": str(resume.user_id) if resume.user_id else None,
            "current_version_id": resume.current_version_id,
            "raw_text": resume.raw_text,
            "structured_json": normalize_resume_json(resume.structured_json),
            "versions": [self.serialize_version(version) for version in versions],
            "latest_analysis": latest_analysis.analysis if latest_analysis else None,
            "updated_at": resume.updated_at,
        }

    async def manual_edit(
        self,
        db: AsyncSession,
        *,
        resume: Resume,
        section: str,
        payload: Any,
        subsection_index: Optional[int],
        change_summary: str,
    ) -> ResumeVersion:
        current = normalize_resume_json(resume.structured_json)
        updated = set_section_value(current, section, payload, subsection_index)
        return await self.versioning.save_version(db, resume=resume, content=updated, change_summary=change_summary)

    async def improve_section(
        self,
        db: AsyncSession,
        *,
        resume: Resume,
        section: str,
        subsection_index: Optional[int],
        user_instruction: Optional[str],
        mode: str,
    ) -> ResumeVersion:
        current = normalize_resume_json(resume.structured_json)
        target = current.get(section)
        original_fragment = target

        if section == "personal_info":
            target_fragment = original_fragment
        elif subsection_index is not None and isinstance(target, list):
            if subsection_index < 0 or subsection_index >= len(target):
                raise ValueError("subsection_index out of range.")
            original_fragment = target[subsection_index]
            target_fragment = original_fragment
        else:
            target_fragment = target

        prompt = IMPROVE_SECTION_SYSTEM_PROMPT if mode == "improve_section" else REGENERATE_BULLETS_SYSTEM_PROMPT
        updated_fragment_raw = await self._rewrite_with_llm(
            system_prompt=prompt,
            current_section=target_fragment,
            user_instruction=user_instruction,
        )
        try:
            parsed_fragment = parse_json_object(updated_fragment_raw)
        except Exception:
            parsed_fragment = original_fragment

        ensure_generated_content_is_grounded(original_fragment, parsed_fragment, section=section)
        updated = set_section_value(current, section, parsed_fragment, subsection_index)
        return await self.versioning.save_version(
            db,
            resume=resume,
            content=updated,
            change_summary=f"{mode} applied to {section}",
        )

    async def apply_suggestion(
        self,
        db: AsyncSession,
        *,
        resume: Resume,
        section: str,
        suggestion_text: str,
        subsection_index: Optional[int],
    ) -> ResumeVersion:
        return await self.improve_section(
            db,
            resume=resume,
            section=section,
            subsection_index=subsection_index,
            user_instruction=suggestion_text,
            mode="apply_suggestion",
        )

    async def improve_full_resume(
        self,
        db: AsyncSession,
        *,
        resume: Resume,
        user_instruction: Optional[str] = None,
    ) -> ResumeVersion:
        """
        Improves all sections of the resume sequentially using AI.
        """
        current = normalize_resume_json(resume.structured_json)
        sections_to_improve = ["experience", "projects", "education", "skills", "achievements"]
        
        updated = deepcopy(current)
        for section in sections_to_improve:
            if section in current and current[section]:
                try:
                    # Reuse existing LLM rewrite logic
                    target_fragment = current[section]
                    prompt = IMPROVE_SECTION_SYSTEM_PROMPT
                    
                    updated_fragment_raw = await self._rewrite_with_llm(
                        system_prompt=prompt,
                        current_section=target_fragment,
                        user_instruction=user_instruction or "Optimize for ATS and clarity.",
                    )
                    parsed_fragment = parse_json_object(updated_fragment_raw)
                    # Grounding check
                    ensure_generated_content_is_grounded(target_fragment, parsed_fragment, section=section)
                    updated[section] = parsed_fragment
                except Exception as e:
                    print(f"Error improving section {section}: {e}")
                    # Continue with other sections if one fails
        
        return await self.versioning.save_version(
            db,
            resume=resume,
            content=updated,
            change_summary="Full resume AI improvement applied",
        )

    async def reanalyze_resume(self, db: AsyncSession, *, resume: Resume) -> Dict[str, Any]:
        analysis = await asyncio.to_thread(
            self.rag_service.analyze_resume,
            resume.raw_text or resume.extracted_text or "",
        )
        cache = ResumeAnalysisCache(resume_id=resume.id, analysis=analysis)
        db.add(cache)
        await db.flush()
        return analysis

    async def commit(self, db: AsyncSession) -> None:
        await db.commit()

    async def rollback(self, db: AsyncSession) -> None:
        await db.rollback()

    async def resolve_or_create_profile_id(self, db: AsyncSession, current_user: Optional[Profile]) -> Optional[UUID]:
        if current_user is None:
            return None

        profile = await db.scalar(select(Profile).where(Profile.email == current_user.email))
        if profile is not None:
            return profile.id

        user_type = current_user.user_type
        inferred_name = current_user.email.split("@")[0].replace(".", " ").title()

        profile = Profile(
            full_name=inferred_name,
            email=current_user.email,
            user_type=user_type,
            status="active",
        )
        db.add(profile)
        await db.flush()
        return profile.id

    def serialize_version(self, version: ResumeVersion) -> Dict[str, Any]:
        return {
            "id": version.id,
            "version_number": version.version_number,
            "change_summary": version.change_summary,
            "created_at": version.created_at,
        }

    async def _rewrite_with_llm(
        self,
        *,
        system_prompt: str,
        current_section: Any,
        user_instruction: Optional[str],
    ) -> str:
        llm = get_llm(temperature=0.2)
        prompt = (
            f"{system_prompt}\n\n"
            f"Current section JSON:\n{current_section}\n\n"
            f"Additional instruction: {user_instruction or 'Keep the same facts, improve quality only.'}\n\n"
            "Return JSON only."
        )
        response = await llm.ainvoke(prompt)
        return response.content

    async def _resolve_student_id(self, db: AsyncSession, user_id: Optional[UUID]):
        if not user_id:
            return None
        return await db.scalar(select(Student.id).where(Student.profile_id == user_id))
