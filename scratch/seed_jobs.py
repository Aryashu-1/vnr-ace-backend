
import asyncio
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add the project root to sys.path to import models
sys.path.append(os.getcwd())

from models.company import Company
from models.placement_drive import PlacementDrive
from core.db import Base

DATABASE_URL = "postgresql+asyncpg://postgres.chevhdkfqfcupjdmkbud:k5kBfYAthCJeg@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

DUMMY_JOBS = [
    {
        "id": "1",
        "companyName": "TechNova Solutions",
        "role": "Full Stack Developer (SDE-1)",
        "package": "14.5 LPA",
        "location": "Bangalore",
        "deadline": "Oct 15, 2026",
        "tags": ["Full Time", "Software", "Remote Eligible"],
        "description": "TechNova Solutions is looking for passionate Full Stack Developers to join our core engineering team. You will be responsible for building scalable web applications and microservices using React, Node.js, and AWS.",
        "criteria": {
            "cgpa": "7.5 & Above",
            "branches": ["CSE", "IT", "ECE"],
            "backlogs": "No active backlogs",
        },
        "skills": ["React.js", "Node.js", "TypeScript", "AWS", "MongoDB"],
        "examRounds": [
            { "round": 1, "name": "Online Coding Assessment", "date": "Oct 18, 2026", "description": "DSA and logical reasoning (90 mins)" },
            { "round": 2, "name": "Technical Interview 1", "date": "Oct 21, 2026", "description": "System Design and Core CS concepts" },
            { "round": 3, "name": "HR & Cultural Fit", "date": "Oct 25, 2026", "description": "Final discussion with HR" },
        ],
        "status": 'open',
        "instructions": [
            "Ensure your resume includes a link to your GitHub profile or portfolio.",
            "Complete the coding assessment before the technical interview.",
            "Prepare to discuss your past projects in depth."
        ]
    },
    {
        "id": "2",
        "companyName": "DataSphere Analytics",
        "role": "Data Scientist",
        "package": "18.0 LPA",
        "location": "Hyderabad",
        "deadline": "Oct 20, 2026",
        "tags": ["Full Time", "Data Science", "AI/ML"],
        "description": "Join DataSphere Analytics to solve complex business problems using advanced machine learning algorithms. You will work on predictive modeling, natural language processing, and deep learning projects.",
        "criteria": {
            "cgpa": "8.0 & Above",
            "branches": ["CSE", "IT"],
            "backlogs": "No history of backlogs",
        },
        "skills": ["Python", "TensorFlow", "SQL", "Machine Learning", "Data Visualization"],
        "examRounds": [
            { "round": 1, "name": "Aptitude & Data Science Quiz", "date": "Oct 25, 2026", "description": "MCQs on Statistics and ML concepts" },
            { "round": 2, "name": "Coding & ML Interview", "date": "Oct 28, 2026", "description": "Live coding and model discussion" },
            { "round": 3, "name": "Managerial Round", "date": "Nov 02, 2026", "description": "Project discussion and culture fit" },
        ],
        "status": 'open',
        "instructions": [
            "Submit your latest resume highlighting ML/Data Science projects.",
            "A portfolio showcasing Kaggle competitions or research papers is highly recommended."
        ],
        "externalRegistrationUrl": "https://careers.datasphere.ai/apply/student-hiring-2026",
        "requiresExternalRegistration": True,
    },
    {
        "id": "3",
        "companyName": "CloudScale Inc",
        "role": "DevOps Engineer",
        "package": "15.0 LPA",
        "location": "Remote",
        "deadline": "Oct 22, 2026",
        "tags": ["Full Time", "Cloud", "Infra"],
        "description": "CloudScale is seeking a talented DevOps Engineer to automate and streamline our deployment processes. Experience with CI/CD pipelines, Kubernetes, and cloud infrastructure is essential.",
        "criteria": {
            "cgpa": "7.0 & Above",
            "branches": ["CSE", "IT", "ECE"],
            "backlogs": "Allowed up to 1 active backlog",
        },
        "skills": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux"],
        "examRounds": [
            { "round": 1, "name": "Linux & Cloud Assessment", "date": "Oct 28, 2026", "description": "Concepts of OS, Networking and Cloud" },
            { "round": 2, "name": "Technical Interview", "date": "Nov 03, 2026", "description": "Deep dive into DevOps tools" },
        ],
        "status": 'applied',
    },
    {
        "id": "4",
        "companyName": "FinTech Global",
        "role": "Backend Engineer",
        "package": "22.5 LPA",
        "location": "Mumbai",
        "deadline": "Oct 12, 2026",
        "tags": ["Full Time", "Finance", "Backend"],
        "description": "Build high-performance, low-latency trading systems for global markets. Strong problem-solving skills and proficiency in C++ or Java are required.",
        "criteria": {
            "cgpa": "8.5 & Above",
            "branches": ["CSE"],
            "backlogs": "No history of backlogs",
        },
        "skills": ["Java", "C++", "Spring Boot", "System Design", "Microservices"],
        "examRounds": [
            { "round": 1, "name": "Advanced Competitive Coding", "date": "Oct 15, 2026", "description": "3 Hard level CP questions" },
            { "round": 2, "name": "System Design Interview", "date": "Oct 18, 2026", "description": "HLD and LLD of scalable systems" },
            { "round": 3, "name": "Engineering Manager Round", "date": "Oct 21, 2026", "description": "Behavioral and technical depth" },
        ],
        "status": 'closed',
    }
]

async def seed():
    async with AsyncSessionLocal() as session:
        for job_data in DUMMY_JOBS:
            # 1. Create or get Company
            company_name = job_data["companyName"]
            result = await session.execute(select(Company).where(Company.name == company_name))
            company = result.scalars().first()
            
            if not company:
                company = Company(
                    id=uuid.uuid4(),
                    name=company_name,
                    sector="Tech" # Default
                )
                session.add(company)
                await session.flush()
            
            # 2. Create PlacementDrive
            try:
                ctc_val = float(job_data["package"].replace(" LPA", ""))
            except:
                ctc_val = 0.0
                
            try:
                deadline_val = datetime.strptime(job_data["deadline"], "%b %d, %2026").date()
            except:
                deadline_val = datetime.now().date()

            criteria_json = {
                "tags": job_data.get("tags", []),
                "description": job_data.get("description", ""),
                "eligibility": job_data.get("criteria", {}),
                "skills": job_data.get("skills", []),
                "exam_rounds": job_data.get("examRounds", []),
                "instructions": job_data.get("instructions", []),
                "location": job_data.get("location", "")
            }

            drive = PlacementDrive(
                id=uuid.uuid4(),
                company_id=company.id,
                role=job_data["role"],
                ctc=ctc_val,
                deadline=deadline_val,
                status=job_data["status"],
                criteria=criteria_json,
                external_registration_url=job_data.get("externalRegistrationUrl"),
                requires_external_registration=job_data.get("requiresExternalRegistration", False)
            )
            session.add(drive)
        
        await session.commit()
        print("Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
