from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import User, Tenant
from app.schemas import UserCreate, UserResponse, UserLogin, TokenResponse
from app.security import hash_password, verify_password, create_jwt_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_session)):

    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    if not tenant.is_active:
        raise HTTPException(status_code=400, detail="Tenant is inactive")

    
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        hashed_password=hash_password(user.password),
        tenant_id=user.tenant_id
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalars().first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_jwt_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email
    )
    return {"access_token": token, "token_type": "bearer"}