import asyncio
import uuid
from datetime import date, timedelta
from sqlalchemy import select
from core.db import async_session
from models.company import Company
from models.placement_drive import PlacementDrive

async def populate():
    async with async_session() as db:
        # Check if we have companies
        companies_result = await db.execute(select(Company))
        companies = companies_result.scalars().all()
        
        if not companies:
            print("No companies found. Creating sample companies first.")
            company_names = ["Google", "Microsoft", "Amazon", "Meta", "Apple", "Netflix", "Adobe", "Salesforce", "Intel", "NVIDIA"]
            for name in company_names:
                db.add(Company(id=uuid.uuid4(), name=name))
            await db.commit()
            companies_result = await db.execute(select(Company))
            companies = companies_result.scalars().all()

        # Check existing drives
        drives_count = (await db.execute(select(PlacementDrive))).scalars().all()
        if len(drives_count) >= 10:
            print(f"Found {len(drives_count)} drives already. Skipping population.")
            return

        roles = ["Software Engineer", "Frontend Developer", "Backend Engineer", "Data Scientist", "DevOps Engineer", "Product Manager", "UI/UX Designer", "Machine Learning Engineer", "Cybersecurity Analyst", "Cloud Architect"]
        
        for i in range(10):
            company = companies[i % len(companies)]
            role = roles[i]
            drive = PlacementDrive(
                id=uuid.uuid4(),
                company_id=company.id,
                role=role,
                ctc=10.0 + (i * 2.5),
                drive_date=date.today() + timedelta(days=(i+1)*5),
                deadline=date.today() + timedelta(days=(i+1)*2),
                status="open",
                requires_external_registration=(i % 3 == 0),
                external_registration_url=f"https://careers.{company.name.lower()}.com/apply" if (i % 3 == 0) else None
            )
            db.add(drive)
            print(f"Added job: {role} at {company.name}")
        
        await db.commit()
        print("Successfully populated 10 sample jobs.")

if __name__ == "__main__":
    asyncio.run(populate())
