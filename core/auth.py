from fastapi import APIRouter, Depends, HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta

from core.db import get_db
from core.auth_utils import verify_password, create_access_token
from core.config import settings
from models.user import User
from models.role import Role
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
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Get role name
    role = await db.get(Role, user.role_id)
    if not role:
        raise HTTPException(status_code=500, detail="Role not found")

    # Token expiry
    expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    # Create JWT token with email & role name
    token = create_access_token(
        data={
            "sub": user.email,
            "role": role.name,
            "user_id": user.id
        },
        expires_delta=expires,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": role.name
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

    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

# Role-based guard
def require_role(*allowed_roles):
    async def role_checker(current_user = Depends(get_current_user)):
        user_role = current_user.role_id  # numeric role_id (1,2,3,4)

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return current_user

    return role_checker