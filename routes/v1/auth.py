from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta

from core.db import get_db
from core.auth_utils import verify_password, create_access_token
from core.config import settings
from models.profile import Profile
from schemas.auth import LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    print(f"🚀 Login request received for: {form_data.username}")
    # Find user by email (username field in form_data)
    result = await db.execute(
        select(Profile).where(Profile.email == form_data.username)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not profile.hashed_password or not verify_password(form_data.password, profile.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Token expiry
    expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    # Create JWT token
    token = create_access_token(
        data={
            "sub": profile.email,
            "role": profile.user_type, # Using user_type as role for simplicity
            "user_id": str(profile.id) # Convert UUID to string
        },
        expires_delta=expires,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=str(profile.id),
            email=profile.email,
            role=profile.user_type
        )
    )

@router.get("/me", response_model=UserResponse)
async def get_me(db: AsyncSession = Depends(get_db)):
    # This will be protected by a dependency later
    # For now, just a placeholder or skeleton
    raise HTTPException(status_code=501, detail="Not implemented yet")
