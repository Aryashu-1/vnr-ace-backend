# agents/placements/shortlisting/services.py

from typing import List, Dict, Any
import re
import faiss
import numpy as np
import pickle
from collections import defaultdict
from sqlalchemy import select
from sentence_transformers import SentenceTransformer
import fitz
import spacy
from pathlib import Path
import os
from agents.core_modules import LLMService
import asyncio
from models.resume import Resume
from models.student import Student

class ResumeShortlister:
    # Path to the FAISS index relative to the project root
    FAISS_PATH = Path("placements/faiss_index")

    def __init__(self):
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        
        index_path = self.FAISS_PATH / "index.faiss"
        metadata_path = self.FAISS_PATH / "metadata.pkl"
        
        if not index_path.exists() or not metadata_path.exists():
            # Fallback for local development or if paths are different
            # Try to find it relative to current file if not in root
            root_index = Path(__file__).parent.parent.parent.parent / "placements" / "faiss_index"
            if (root_index / "index.faiss").exists():
                index_path = root_index / "index.faiss"
                metadata_path = root_index / "metadata.pkl"
            else:
                raise FileNotFoundError(f"FAISS index not found at {index_path} or {root_index}")

        self.index = faiss.read_index(str(index_path))
        with open(str(metadata_path), "rb") as f:
            self.metadata = pickle.load(f)

    def get_embedding(self, text: str) -> list:
        embedding = self.model.encode(text)
        return embedding.tolist()

    def extract_text_from_pdf(self, path):
        doc = fitz.open(path)
        text = " ".join(page.get_text() for page in doc)
        
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        
        filtered_tokens = [token.lemma_ for token in doc if token.is_alpha]
        return " ".join(filtered_tokens)

    def chunk_text(self, text, size=800):
        return [text[i:i+size] for i in range(0, len(text), size)]

    def match_job(self, job_description, top_k=5, allowed_roll_nos: List[str] = None):
        query_embedding = np.array([self.get_embedding(job_description)], dtype="float32")
        faiss.normalize_L2(query_embedding)

        # Increase search limit significantly to ensure we find enough unique resumes
        # (each resume might have many matching chunks)
        search_k = 500 if allowed_roll_nos else 100
        scores, indices = self.index.search(query_embedding, search_k)

        resume_hits = defaultdict(list)

        for idx, score in zip(indices[0], scores[0]):
            if idx == -1: continue
            hit = self.metadata[idx]
            
            # Extract roll number from resume_id (filename)
            # Assuming format: 21071A0501.pdf or similar
            resume_id = hit["resume_id"]
            roll_no = resume_id.split('.')[0]
            
            if allowed_roll_nos and roll_no not in allowed_roll_nos:
                continue

            hit["score"] = float(score)
            resume_hits[resume_id].append(hit)

        ranked = sorted(
            resume_hits.items(),
            key=lambda x: max(chunk["score"] for chunk in x[1]),
            reverse=True
        )

        return ranked[:top_k]

    def run(self, job_description, top_k=5, allowed_roll_nos: List[str] = None):
        top_matches = self.match_job(job_description, top_k=top_k, allowed_roll_nos=allowed_roll_nos)
        
        # Format for API response
        results = []
        for resume_id, chunks in top_matches:
            results.append({
                "resume_id": resume_id,
                "roll_no": resume_id.split('.')[0],
                "score": float(max(chunk["score"] for chunk in chunks)),
                "matched_chunks": chunks[:2] # Return top 2 matching snippets
            })
            
        return results

    async def explain_matches(self, jd_text: str, candidates: List[Dict], llm: LLMService):
        """
        Uses LLM to summarize why each candidate is a good match based on their fragments.
        Runs in parallel for speed.
        """
        if not candidates or not llm:
            return candidates

        async def explain_single(cand):
            snippets = " | ".join([c["text"] for c in cand.get("matched_chunks", [])])
            prompt = f"""
            Job Description: {jd_text}
            Candidate Resume Snippets: {snippets}
            
            Provide a detailed, professional explanation (2-3 sentences) of why this student is a good match for this role. 
            Explicitly mention matching skills, projects, or experiences found in their resume snippets that align with the Job Description.
            Be specific and informative.
            """
            try:
                reason = await asyncio.to_thread(llm.invoke_text, "You are a recruitment specialist providing detailed technical match justifications.", prompt)
                cand["match_reason"] = reason.strip()
            except Exception as e:
                cand["match_reason"] = "Could not generate match explanation."
            return cand

        tasks = [explain_single(c) for c in candidates]
        return await asyncio.gather(*tasks)


class ShortlistingService:
    """
    Service wrapper for the Shortlisting agent.
    """
    def __init__(self, llm: LLMService = None):
        self.shortlister = ResumeShortlister()
        self.llm = llm

    def shortlist(self, jd_text: str, top_k: int = 5, allowed_roll_nos: List[str] = None) -> List[Dict[str, Any]]:
        return self.shortlister.run(jd_text, top_k=top_k, allowed_roll_nos=allowed_roll_nos)

    async def shortlist_from_db(
        self,
        db,
        jd_text: str,
        top_k: int = 5,
        branch: str | None = None,
        min_cgpa: float | None = None,
        allowed_roll_nos: List[str] | None = None,
    ) -> List[Dict[str, Any]]:
        from models.profile import Profile
        from models.department import Department
        
        stmt = (
            select(Resume, Student, Profile)
            .join(Student, Student.id == Resume.student_id)
            .outerjoin(Profile, Profile.id == Student.profile_id)
            .outerjoin(Department, Department.id == Student.department_id)
            .where(Resume.extracted_text.is_not(None))
        )
        if branch:
            stmt = stmt.where(Department.name == branch)
        if min_cgpa is not None:
            stmt = stmt.where(Student.cgpa >= min_cgpa)
        if allowed_roll_nos:
            stmt = stmt.where(Student.roll_no.in_(allowed_roll_nos))

        rows = (await db.execute(stmt)).all()
        if not rows:
            return []

        jd_tokens = {token for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]+", jd_text.lower()) if len(token) > 2}
        ranked = []
        for resume, student, profile in rows:
            text = (resume.extracted_text or "").lower()
            if not text:
                continue
            matched = [token for token in jd_tokens if token in text]
            if not matched:
                continue
            snippet_start = max(text.find(matched[0]) - 120, 0)
            snippet = (resume.extracted_text or "")[snippet_start: snippet_start + 280].strip()
            score = round(len(matched) / max(len(jd_tokens), 1), 4)
            
            student_name = profile.full_name if profile else student.roll_no
            
            ranked.append(
                {
                    "resume_id": resume.id,
                    "roll_no": student.roll_no,
                    "student_name": student_name,
                    "score": score,
                    "matched_chunks": [{"text": snippet, "matched_keywords": matched[:8]}],
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_k]

    async def explain_matches(self, jd_text: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.llm:
            # Fallback if no LLM provided
            self.llm = LLMService()
        return await self.shortlister.explain_matches(jd_text, candidates, self.llm)
