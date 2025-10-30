from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.models.users import User

router = APIRouter()

@router.get("/auth/whoami")
async def auth_whoami(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "is_admin": current_user.is_admin}
