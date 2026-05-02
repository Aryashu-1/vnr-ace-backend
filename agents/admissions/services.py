import os
import re
from typing import Dict, Any
from agents.admissions.utils import sanitize_key

class AdmissionsDataService:
    DEPT_DIR = "data/departments"
    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
        "i", "in", "is", "it", "of", "on", "or", "please", "the", "to", "what",
        "when", "where", "which", "who", "with", "about", "tell", "me", "can",
        "you", "my", "we", "our", "do", "does",
    }

    _cache = {}

    @classmethod
    async def fetch_departments_from_db(cls) -> Dict[str, Any]:
        """
        Fetches department info from the database and updates the local cache.
        """
        from core.db import AsyncSessionLocal
        from sqlalchemy import text
        from agents.admissions.utils import sanitize_key

        new_data = {}
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT name, description FROM departments"))
                rows = result.fetchall()
                for name, description in rows:
                    key = sanitize_key(name)
                    new_data[key] = {
                        "name": name,
                        "content": description or ""
                    }
            cls._cache = new_data
        except Exception as e:
            print(f"Error fetching departments from DB: {e}")
            # If DB fails, try to fallback to local files if any exist
            if not cls._cache:
                cls._cache = cls.load_departments_data_from_files()
        
        return cls._cache

    @classmethod
    def load_departments_data(cls) -> Dict[str, Any]:
        """
        Returns the current cache. If empty, it should have been initialized at startup.
        If still empty, it falls back to local files for safety.
        """
        if not cls._cache:
            return cls.load_departments_data_from_files()
        return cls._cache

    @classmethod
    def load_departments_data_from_files(cls) -> Dict[str, Any]:
        """
        Fallback: Loads department information from the data/departments directory.
        """
        departments_data = {}
        if os.path.exists(cls.DEPT_DIR):
            for filename in os.listdir(cls.DEPT_DIR):
                if filename.endswith(".txt"):
                    filepath = os.path.join(cls.DEPT_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            key = sanitize_key(filename)
                            departments_data[key] = {
                                "name": os.path.splitext(filename)[0],
                                "content": content
                            }
                    except Exception as e:
                        print(f"Error reading {filename}: {e}")
        return departments_data

    @classmethod
    def _tokenize(cls, text: str) -> list[str]:
        return [
            token for token in re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
            if token not in cls.STOP_WORDS and len(token) > 1
        ]

    @classmethod
    def _best_department_match(cls, message: str, departments_data: Dict[str, Any]) -> str | None:
        message_lower = (message or "").lower()
        tokens = set(cls._tokenize(message))

        best_key = None
        best_score = 0

        for key, info in departments_data.items():
            score = 0
            dept_name = info["name"].lower()
            key_parts = set(key.split("_"))

            if dept_name in message_lower or (dept_name.replace("department", "branch") in message_lower):
                score += 5
            if key.replace("_", " ") in message_lower or (key.replace("_", " ").replace("department", "branch") in message_lower):
                score += 4
            score += len(tokens & key_parts) * 2


            if score > best_score:
                best_score = score
                best_key = key

        return best_key if best_score > 0 else None

    @classmethod
    def _pick_relevant_sentences(cls, content: str, message: str, limit: int = 3) -> list[str]:
        query_tokens = set(cls._tokenize(message))
        if not content.strip():
            return []

        sentences = re.split(r"(?<=[.!?])\s+|\n+", content)
        scored_sentences = []

        for sentence in sentences:
            cleaned = sentence.strip()
            if len(cleaned) < 30:
                continue
            sentence_tokens = set(cls._tokenize(cleaned))
            score = len(query_tokens & sentence_tokens)
            if score > 0:
                scored_sentences.append((score, cleaned))

        scored_sentences.sort(key=lambda item: item[0], reverse=True)
        return [sentence for _, sentence in scored_sentences[:limit]]

    @classmethod
    def build_fallback_response(cls, message: str) -> Dict[str, str]:
        departments_data = cls.load_departments_data()
        dept_key = cls._best_department_match(message, departments_data)

        if dept_key:
            dept_info = departments_data[dept_key]
            relevant = cls._pick_relevant_sentences(dept_info["content"], message)
            if relevant:
                return {
                    "route": "department_query",
                    "reply": " ".join(relevant),
                }

        admissions_info = departments_data.get("admissions")
        if admissions_info:
            relevant = cls._pick_relevant_sentences(admissions_info["content"], message)
            if relevant:
                return {
                    "route": "faq",
                    "reply": " ".join(relevant),
                }

        placements_info = departments_data.get("placements")
        if placements_info:
            relevant = cls._pick_relevant_sentences(placements_info["content"], message)
            if relevant:
                return {
                    "route": "faq",
                    "reply": " ".join(relevant),
                }

        return {
            "route": "fallback_unavailable",
            "reply": "The admissions assistant is temporarily running in fallback mode. Please retry shortly or ask a department-specific admissions question.",
        }
