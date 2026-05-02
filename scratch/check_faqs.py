import asyncio
from sqlalchemy import text
from core.db import engine

async def check_faqs():
    async with engine.connect() as conn:
        print("Checking for faqs table...")
        table_exists = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'faqs'
            )
        """))
        exists = table_exists.scalar()
        print(f"Table 'faqs' exists: {exists}")
        
        if exists:
            result = await conn.execute(text("SELECT count(*) FROM faqs"))
            count = result.scalar()
            print(f"Number of FAQs in DB: {count}")
            
            if count > 0:
                result = await conn.execute(text("SELECT question, category FROM faqs LIMIT 5"))
                faqs = result.all()
                for f in faqs:
                    print(f"[{f.category}] {f.question}")

if __name__ == "__main__":
    asyncio.run(check_faqs())
