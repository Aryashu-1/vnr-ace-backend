from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.auth_utils import decode_access_token
from core.db import get_db
from models.user import User
from models.role import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    # Decode JWT
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing user ID")

    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# ROLE CHECKER
def role_required(required_role: str):
    async def role_checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        # Load role name for the user
        result = await db.execute(select(Role).where(Role.id == user.role_id))
        role = result.scalar_one_or_none()

        if not role:
            raise HTTPException(status_code=403, detail="Role not found")

        if role.name != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Requires '{required_role}' role. Current: '{role.name}'",
            )

        return user

    return role_checker
