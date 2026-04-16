from fastapi import Depends, HTTPException, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import User, Tenant, TenantAPIKey
from app.security import decode_jwt_token

bearer = HTTPBearer()

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session)
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_jwt_token(token)
    result = await db.execute(select(User).where(User.id == payload["user_id"]))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_admin_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
) -> User:
    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="You do not belong to an organization")
    
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalars().first()
    if tenant.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def chat_user(
        x_api_key: str = Header(None),
        db: AsyncSession = Depends(get_session)
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    result = await db.execute(
        select(User)
        .join(TenantAPIKey, TenantAPIKey.tenant_id == User.tenant_id)
        .where(TenantAPIKey.req_key == x_api_key)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user