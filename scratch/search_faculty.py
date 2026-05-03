import asyncio
from sqlalchemy import select
from core.db import async_session
from models.profile import Profile

async def main():
    async with async_session() as db:
        q = select(Profile).where(Profile.full_name.ilike('%Sneha%'))
        res = await db.execute(q)
        profiles = res.scalars().all()
        for p in profiles:
            print(f"Found: {p.full_name} ({p.id})")

        q = select(Profile).where(Profile.full_name.ilike('%Venkatesh%'))
        res = await db.execute(q)
        profiles = res.scalars().all()
        for p in profiles:
            print(f"Found: {p.full_name} ({p.id})")

if __name__ == "__main__":
    asyncio.run(main())
