from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.database import get_db
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead, UserRegister
from app.crud.users import get_user_by_username, authenticate_user, create_user
from app.auth_utils import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.dependencies.auth import get_current_user
from app.models.registration_token import RegistrationToken

router = APIRouter()

@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserRead)
async def read_users_me(current_user: UserRead = Depends(get_current_user)):
    return current_user

@router.post("/register", response_model=UserRead)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_username(db, user_in.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

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
    new_user = await create_user(db, user_create)
    return new_user
