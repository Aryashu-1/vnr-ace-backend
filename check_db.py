import asyncio
from sqlalchemy import select, func
from core.db import async_session
from models.placement_offer_v2 import PlacementOfferV2
from models.student import Student
from models.company import Company
from models.placement_drive import PlacementDrive

async def main():
    async with async_session() as db:
        offers = (await db.execute(select(func.count(PlacementOfferV2.id)))).scalar()
        students = (await db.execute(select(func.count(Student.id)))).scalar()
        companies = (await db.execute(select(func.count(Company.id)))).scalar()
        drives = (await db.execute(select(func.count(PlacementDrive.id)))).scalar()
        print(f"Offers: {offers}")
        print(f"Students: {students}")
        print(f"Companies: {companies}")
        print(f"Drives: {drives}")

if __name__ == "__main__":
    asyncio.run(main())
