import json
import os
from .constants import DATA_BASE_PATH

def load_company_data(company_name: str) -> dict:
    """
    Loads company-specific interview data from JSON.
    """
    normalized_name = (company_name or "").strip()
    if not normalized_name:
        return {"company": company_name, "experiences": [], "questions": []}

    file_path = os.path.join(DATA_BASE_PATH, f"{normalized_name.lower()}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    shared_file_path = os.path.join("data", "placements", "interview_experiences.json")
    if os.path.exists(shared_file_path):
        with open(shared_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for company in data.get("companies", []):
            if company.get("name", "").strip().lower() == normalized_name.lower():
                questions = []
                for experience in company.get("experiences", []):
                    for round_info in experience.get("rounds", []):
                        questions.extend(round_info.get("questions", []))

                return {
                    "company": company.get("name", normalized_name),
                    "experiences": company.get("experiences", []),
                    "questions": questions,
                    "summary": company.get("summary", {}),
                    "global_patterns": data.get("global_patterns", {}),
                }

    return {"company": company_name, "experiences": [], "questions": []}

def filter_questions_by_keyword(questions: list, user_query: str, topics: list = None) -> list:
    """
    Filters questions based on user query keywords and optional tags.
    """
    query_lower = user_query.lower()
    filtered = []
    
    for q in questions:
        # Check if query matches question content or tags
        matches_query = query_lower in q.get("question", "").lower() or \
                        query_lower in q.get("content", "").lower()
        
        # Check if q's tags match user's selected topics
        matches_topic = False
        if topics:
            q_tags = [t.lower() for t in q.get("tags", [])]
            matches_topic = any(topic.lower() in q_tags for topic in topics)
        
        if matches_query or matches_topic:
            filtered.append(q)
            
    return filtered
