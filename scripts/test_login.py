import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import AsyncSessionLocal
from core.auth import login
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import HTTPException

async def test_login():
    async with AsyncSessionLocal() as db:
        form_data = OAuth2PasswordRequestForm(username="admina@vnr.com", password="admin123", scope="", client_id=None, client_secret=None, grant_type="password")
        try:
            res = await login(form_data=form_data, db=db)
            print("Login successful:", res)
        except HTTPException as e:
            print("HTTPException:", e.detail)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_login())
