from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.crud.users import get_user_by_username
from app.auth_utils import SECRET_KEY, ALGORITHM
# from app.schemas.token import TokenData  # optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username_claim = payload.get("sub")
        if not isinstance(username_claim, str) or not username_claim:
            raise cred_exc
    except JWTError:
        raise cred_exc

    user = await get_user_by_username(db, username_claim)
    if user is None:
        raise cred_exc

    # 👇 add credentialing check
    if not getattr(user, "credentialing_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credentialing expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user