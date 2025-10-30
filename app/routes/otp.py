from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.models.registration_token import RegistrationToken
import secrets
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/otp")
async def generate_otp(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Ensure only admins can generate OTPs
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")

    otp = secrets.token_urlsafe(8)
    token = RegistrationToken(
        token=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return {"otp": token.token, "expires_at": token.expires_at}