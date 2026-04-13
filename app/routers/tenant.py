from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.dependencies import get_current_user, get_admin_user
import secrets
from app.models import Tenant, User
from app.schemas import TenantCreate, TenantOnBoarding
from app.security import create_jwt_token

router = APIRouter(prefix="/org", tags=["organization"])

@router.post("/create", response_model=TenantOnBoarding)
async def create_tenant(
    response: Response,
    tenant: TenantCreate, 
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
    ):
    result = await db.execute(select(Tenant).where(Tenant.name == tenant.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Tenant already exists")

    new_tenant = Tenant(
        name=tenant.name, 
        slug = tenant.slug,
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

    response.set_cookie(
        key="access_token",
        value=new_token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/"      
    )

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "tenant": new_tenant
    }

@router.post("/invites")
async def generate_invite(
    db: AsyncSession = Depends(get_session),
    admin: User = Depends(get_admin_user)
):
    new_code = secrets.token_hex(4).upper()
    result = await db.execute(select(Tenant).where(Tenant.id == admin.tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.invite_code = new_code
    await db.commit()

    return {"code": new_code}

@router.post("/join", response_model=TenantOnBoarding)
async def join_tenant(
    response: Response,
    payload: dict,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
    ):
    invite_code = payload.get("invite_code")
    result = await db.execute(select(Tenant).where(Tenant.invite_code == invite_code))
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(status_code=400, detail="Invalid invite code")

    current_user.tenant_id = tenant.id
    await db.commit()
    await db.refresh(tenant)

    new_token = create_jwt_token(
        user_id= str(current_user.id),
        tenant_id=str(tenant.id),
        email=current_user.email
    )

    response.set_cookie(
        key="access_token",
        value=new_token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/"      
    )

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "tenant": tenant
    }
