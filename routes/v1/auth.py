from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta

from core.db import get_db
from core.auth_utils import verify_password, create_access_token
from core.config import settings
from models.user import User
from models.role import Role
from schemas.auth import LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # Find user by email (username field in form_data)
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Get role name
    role = await db.get(Role, user.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User role configuration error"
        )

    # Token expiry
    expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    # Create JWT token
    token = create_access_token(
        data={
            "sub": user.email,
            "role": role.name,
            "user_id": user.id
        },
        expires_delta=expires,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=role.name
        )
    )

@router.get("/me", response_model=UserResponse)
async def get_me(db: AsyncSession = Depends(get_db)):
    # This will be protected by a dependency later
    # For now, just a placeholder or skeleton
    raise HTTPException(status_code=501, detail="Not implemented yet")
