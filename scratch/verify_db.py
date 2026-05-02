import asyncio
from core.db import engine
from sqlalchemy import text

async def verify():
    async with engine.connect() as conn:
        try:
            res = await conn.execute(text("SELECT attendance FROM students LIMIT 1"))
            print("Students table has 'attendance' column.")
            
            res = await conn.execute(text("SELECT code FROM departments LIMIT 1"))
            print("Departments table has 'code' column.")
            
            res = await conn.execute(text("SELECT hashed_password FROM profiles LIMIT 1"))
            print("Profiles table has 'hashed_password' column.")
            
            res = await conn.execute(text("SELECT deadline FROM placement_drives LIMIT 1"))
            print("PlacementDrives table has 'deadline' column.")
            
            print("VERIFICATION SUCCESSFUL")
        except Exception as e:
            print(f"VERIFICATION FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
