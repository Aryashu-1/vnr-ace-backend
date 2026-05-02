import json
import asyncio
import os
import sys
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.db import AsyncSessionLocal
from models.company import Company
from models.interview_experience import InterviewExperience
from models.interview_round import InterviewRound
from models.interview_question import InterviewQuestion

async def migrate_interview_data():
    json_path = os.path.join("data", "placements", "interview_experiences.json")
    if not os.path.exists(json_path):
        print(f"JSON file not found at {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    async with AsyncSessionLocal() as session:
        print("Starting migration...")
        
        for company_json in data.get("companies", []):
            company_name = company_json.get("name")
            print(f"Processing company: {company_name}")
            
            # 1. Get or Create Company
            result = await session.execute(select(Company).where(Company.name == company_name))
            company = result.scalar_one_or_none()
            
            if not company:
                company = Company(name=company_name)
                session.add(company)
                await session.flush()
            
            # 2. Process Experiences
            for exp_json in company_json.get("experiences", []):
                experience = InterviewExperience(
                    company_id=company.id,
                    role=company_name + " Candidate",
                    overall_experience=f"Experience for {exp_json.get('candidate')}",
                    difficulty_level=company_json.get("summary", {}).get("difficulty", "Medium"),
                    tips=", ".join(company_json.get("summary", {}).get("focus", []))
                )
                session.add(experience)
                await session.flush()
                
                # 3. Process Rounds
                for i, round_json in enumerate(exp_json.get("rounds", [])):
                    round_obj = InterviewRound(
                        experience_id=experience.id,
                        round_type=round_json.get("round", "Technical"),
                        round_order=i + 1
                    )
                    session.add(round_obj)
                    await session.flush()
                    
                    # 4. Process Questions
                    for q_json in round_json.get("questions", []):
                        question = InterviewQuestion(
                            round_id=round_obj.id,
                            question_text=q_json.get("question"),
                            topic=", ".join(q_json.get("tags", [])),
                            difficulty="Medium"
                        )
                        session.add(question)
        
        await session.commit()
        print("✓ Interview data migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate_interview_data())
