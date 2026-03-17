from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import Tenant
from app.schemas import TenantCreate, TenantResponse

router = APIRouter(prefix="/tenant", tags=["tenant"])

@router.post("/", response_model=TenantResponse)
async def create_tenant(tenant: TenantCreate, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Tenant).where(Tenant.name == tenant.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Tenant already exists")

    new_tenant = Tenant(name=tenant.name)
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)
    return new_tenant