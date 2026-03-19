from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.registration_token import RegistrationToken
from app.schemas.user import UserCreate, UserRead, UserRegister
from app.crud.users import create_user, get_user_by_username

router = APIRouter()

@router.post("/register", response_model=UserRead)
async def register_user(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if username already exists
    existing_user = await get_user_by_username(db, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    token_result = await db.execute(
        select(RegistrationToken).where(RegistrationToken.token == user_in.otp)
    )
    registration_token = token_result.scalar_one_or_none()
    if not registration_token:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if registration_token.used:
        raise HTTPException(status_code=400, detail="OTP already used")
    if registration_token.expires_at and registration_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    registration_token.used = True
    user_create = UserCreate(username=user_in.username, password=user_in.password)
    return await create_user(db, user_create)
