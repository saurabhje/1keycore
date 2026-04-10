from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.dependencies import get_current_user
from app.models import Tenant, User
from app.schemas import TenantCreate, TenantOnBoarding
from app.security import create_jwt_token

router = APIRouter(prefix="/tenant", tags=["tenant"])

@router.post("/", response_model=TenantOnBoarding)
async def create_tenant(
    tenant: TenantCreate, 
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
    ):
    result = await db.execute(select(Tenant).where(Tenant.name == tenant.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Tenant already exists")

    new_tenant = Tenant(
        name=tenant.name, 
        admin_id = current_user.id,
        is_active=True)
    
    db.add(new_tenant)
    await db.flush()
    current_user.tenant_id = new_tenant.id

    await db.commit()
    await db.refresh(new_tenant)

    new_token = create_jwt_token(
        user_id= str(current_user.id),
        tenant_id=str(new_tenant.id),
        email=current_user.email
    )

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "tenant": new_tenant
    }