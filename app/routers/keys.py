from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_session
from app.models import TenantAPIKey, User
from app.dependencies import get_admin_user
from app.security import encrypt_api_key
from app.schemas import APIKeyCreate, APIKeyResponse, APIKeyCreateResponse
import secrets
router = APIRouter(prefix="/keys", tags=["keys"])

SUPPORTED_PROVIDERS = ["openai", "anthropic", "gemini", "groq", "mistral", "cohere"]

@router.post("/add", response_model=APIKeyCreateResponse)
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
    
    req_key = "sk-"+secrets.token_urlsafe(24)

    new_key = TenantAPIKey(
        tenant_id=current_user.tenant_id,
        provider=payload.provider,
        encrypted_key=encrypt_api_key(payload.api_key),
        req_key=req_key
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    return {
    "api_key": req_key
}

@router.get("/list", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session)
):
    result = await db.execute(
        select(TenantAPIKey).where(TenantAPIKey.tenant_id == current_user.tenant_id)
    )
    keys = result.scalars().all()
    return keys

@router.delete("/{key_id}", status_code=200)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Permanently deletes an API key from the system.
    """
    stmt = delete(TenantAPIKey).where(
        TenantAPIKey.id == key_id,
        TenantAPIKey.tenant_id == current_user.tenant_id
    )

    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="API Key not found."
        )

    return {"message": "API key revoked successfully", "id": key_id}