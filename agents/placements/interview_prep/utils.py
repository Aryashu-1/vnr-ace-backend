import json
import os
from .constants import DATA_BASE_PATH

def load_company_data(company_name: str) -> dict:
    """
    Loads company-specific interview data from JSON.
    """
    file_path = os.path.join(DATA_BASE_PATH, f"{company_name.lower()}.json")
    if not os.path.exists(file_path):
        return {"company": company_name, "questions": []}
    
    with open(file_path, "r") as f:
        return json.load(f)

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
