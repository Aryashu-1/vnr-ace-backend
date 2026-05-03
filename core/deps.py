from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.auth_utils import decode_access_token
from core.db import get_db
from models.profile import Profile

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

    # Fetch profile
    result = await db.execute(
        select(Profile).where(Profile.id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=401, detail="User not found")

    return profile

# ROLE CHECKER
def role_required(required_role: str):
    async def role_checker(
        profile: Profile = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        if profile.user_type != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Requires '{required_role}' role. Current: '{profile.user_type}'",
            )

        return profile

    return role_checker

def roles_required(allowed_roles: list[str]):
    async def role_checker(
        profile: Profile = Depends(get_current_user),
    ):
        if profile.user_type not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of {allowed_roles} roles. Current: '{profile.user_type}'",
            )

        return profile

    return role_checker

