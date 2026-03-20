from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import User, Tenant
from app.security import decode_jwt_token

bearer = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_session)
) -> User:
    payload = decode_jwt_token(credentials.credentials)
    result = await db.execute(select(User).where(User.id == payload["user_id"]))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_admin_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
) -> User:
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalars().first()
    if tenant.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user