from typing import List, Dict, Any
from .utils import filter_questions_by_keyword

class InterviewPrepService:
    @staticmethod
    def get_relevant_questions(company_data: Dict[str, Any], user_query: str, topics: List[str] = None) -> List[Dict[str, Any]]:
        """
        Filters the full company dataset for relevant questions based on query and topics.
        """
        all_questions = company_data.get("questions", [])
        if not all_questions:
            return []
            
        # Basic keyword filtering for now
        return filter_questions_by_keyword(all_questions, user_query, topics)
