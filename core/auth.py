from fastapi import APIRouter, Depends, HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta

from core.db import get_db
from core.auth_utils import verify_password, create_access_token
from core.config import settings
from models.profile import Profile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.auth_utils import decode_access_token


router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # Find user by email
    result = await db.execute(
        select(Profile).where(Profile.email == form_data.username)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not profile.hashed_password or not verify_password(form_data.password, profile.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Token expiry
    expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    # Create JWT token with email & role name
    token = create_access_token(
        data={
            "sub": profile.email,
            "role": profile.user_type,
            "user_id": str(profile.id)
        },
        expires_delta=expires,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(profile.id),
            "email": profile.email,
            "role": profile.user_type
        }
    }

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch profile
    result = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    return profile

# Role-based guard
def require_role(*allowed_roles):
    async def role_checker(current_user: Profile = Depends(get_current_user)):
        user_role = current_user.user_type  # string role e.g. 'admin', 'faculty', 'student'

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return current_user

    return role_checker