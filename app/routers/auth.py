from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import User, Tenant
from app.schemas import UserCreate, UserResponse, UserLogin, TokenResponse
from app.security import hash_password, verify_password, create_jwt_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_session)):
    
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        name=user.name,
        hashed_password=hash_password(user.password),
    )
    db.add(new_user)
    await db.commit()
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    response: Response, 
    db: AsyncSession = Depends(get_session)):

    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Email not found")
    
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = create_jwt_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        email=user.email
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True, 
        secure=True,
        samesite="lax",
        max_age=24 * 3600,
        domain='.saurabh.codes',
        path="/"
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout", status_code=200)
async def logout(response: Response):
    """
    Clears the HttpOnly JWT cookie to log the user out.
    """
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True,
        samesite="lax",
        domain=".saurabh.codes",  
        path="/"
    )
    return {"message": "Successfully logged out"}