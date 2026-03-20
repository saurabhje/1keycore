from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import TenantAPIKey, User
from app.dependencies import get_admin_user
from app.security import encrypt_api_key
from app.schemas import APIKeyCreate, APIKeyResponse

router = APIRouter(prefix="/keys", tags=["keys"])

SUPPORTED_PROVIDERS = ["openai", "anthropic", "gemini", "groq", "mistral", "cohere"]

@router.post("/", response_model=APIKeyResponse)
async def register_api_key(
    payload: APIKeyCreate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session)
):
    if payload.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Provider must be one of {SUPPORTED_PROVIDERS}")

    result = await db.execute(
        select(TenantAPIKey).where(
            TenantAPIKey.tenant_id == current_user.tenant_id,
            TenantAPIKey.provider == payload.provider
        )
    )
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Key for {payload.provider} already registered")

    new_key = TenantAPIKey(
        tenant_id=current_user.tenant_id,
        provider=payload.provider,
        encrypted_key=encrypt_api_key(payload.api_key)
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    return new_key