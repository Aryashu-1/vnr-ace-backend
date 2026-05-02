from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from models.interview_question import InterviewQuestion
from models.interview_round import InterviewRound
from models.interview_experience import InterviewExperience
from models.company import Company

class InterviewPrepRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_questions_by_company(self, company_name: str, query: str = "", topics: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches questions for a specific company from the database.
        """
        stmt = (
            select(
                InterviewQuestion.question_text.label("question"),
                InterviewQuestion.topic.label("tags"),
                InterviewRound.round_type.label("round"),
                Company.name.label("company")
            )
            .join(InterviewRound, InterviewQuestion.round_id == InterviewRound.id)
            .join(InterviewExperience, InterviewRound.experience_id == InterviewExperience.id)
            .join(Company, InterviewExperience.company_id == Company.id)
            .where(Company.name.ilike(f"%{company_name}%"))
        )

        if query:
            keywords = query.split()
            word_filters = []
            for word in keywords:
                if len(word) > 2: # Ignore small words like 'and', 'the'
                    word_filters.append(InterviewQuestion.question_text.ilike(f"%{word}%"))
                    word_filters.append(InterviewQuestion.topic.ilike(f"%{word}%"))
            
            if word_filters:
                stmt = stmt.where(or_(*word_filters))

        if topics:
            topic_filters = [InterviewQuestion.topic.ilike(f"%{t}%") for t in topics]
            stmt = stmt.where(or_(*topic_filters))

        result = await self.session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_company_experiences(self, company_name: str) -> List[Dict[str, Any]]:
        """
        Fetches interview experiences for a company.
        """
        stmt = (
            select(InterviewExperience)
            .join(Company, InterviewExperience.company_id == Company.id)
            .where(Company.name.ilike(f"%{company_name}%"))
        )
        result = await self.session.execute(stmt)
        experiences = result.scalars().all()
        return [
            {
                "difficulty": exp.difficulty_level,
                "tips": exp.tips,
                "role": exp.role
            } for exp in experiences
        ]

class InterviewPrepService:
    # Deprecated: Kept for backwards compatibility if needed during transition
    @staticmethod
    def get_relevant_questions(company_data: Dict[str, Any], user_query: str, topics: List[str] = None) -> List[Dict[str, Any]]:
        return []
