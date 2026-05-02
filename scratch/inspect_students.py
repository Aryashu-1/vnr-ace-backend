import asyncio
from sqlalchemy import text
from core.db import engine

async def inspect_table():
    async with engine.connect() as conn:
        print("Inspecting columns of students...")
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'students'
        """))
        columns = result.all()
        for col in columns:
            print(f"{col.column_name}: {col.data_type}")

if __name__ == "__main__":
    asyncio.run(inspect_table())
