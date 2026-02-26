from fastapi import FastAPI
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.security import hash_password, verify_password
from app.models import Tenant, User
from app.database import get_session
from app.schemas import TenantCreate, TenantResponse, UserCreate, UserResponse
from .database import init_db



app = FastAPI(title="Multi-Tenant SaaS API")

@app.on_event("startup")
async def on_startup():
    """Initialize the database on application startup."""
    await init_db()
     
@app.post("/tenant", response_model=TenantResponse)
async def create_tenant(tenant: TenantCreate, db: AsyncSession = Depends(get_session)):
    """Create a new tenant."""
    result = await db.execute(select(Tenant).where(Tenant.name == tenant.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Tenant with this name already exists")
    new_tenant = Tenant(name=tenant.name)
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)
    return new_tenant

@app.post("/user", response_model=UserResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_session)):
    """Create a new user under a tenant."""
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    hashed_password = hash_password(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password, tenant_id=user.tenant_id)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
