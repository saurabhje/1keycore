from fastapi import HTTPException, Depends, APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.dependencies import get_current_user
from app.models import User, TenantAPIKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.security import decrypt_api_key
from app.helpers.rate_limiter import check_rpm_token_bucket, check_tpm, concurrency_acquire, release_concurrency
from app.helpers.redis_keys import RedisKeys
from app.helpers.constants import PROVIDER_MODELS, PROVIDER_URLS
from app.helpers.providers import call_anthropic, call_cohere, call_gemini, call_openai

router = APIRouter(prefix="/chat", tags=["chat"])
user_rpm = 20
tenant_rpm = 200
conc_limit_user = 3
conc_limit_tenant = 20
tpm_limit_user = 1000
tpm_limit_tenant = 5000

def get_provider(model: str) -> str:
    for provider, models in PROVIDER_MODELS.items():
        if model in models:
            return provider
    raise HTTPException(status_code=400, detail=f"Unknown model '{model}'. Check supported models.")

@router.post("/", response_model=ChatResponse)
async def chat(
        request: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_session)
):
    user_id = str(current_user.id)
    tenant_id = str(current_user.tenant_id)

    if not check_rpm_token_bucket(RedisKeys.rpm_tenant(tenant_id), tenant_rpm):
        raise HTTPException(status_code=429, detail="Tenant RPM limit exceeded")
    if not check_rpm_token_bucket(RedisKeys.rpm_user(tenant_id, user_id), user_rpm):
        raise HTTPException(status_code=429, detail="User RPM limit exceeded")
    if not check_tpm(RedisKeys.tpm_tenant(tenant_id), tpm_limit_tenant, 100):
        raise HTTPException(status_code=429, detail="Tenant TPM limit exceeded")
    if not check_tpm(RedisKeys.tpm_user(tenant_id, user_id), tpm_limit_user, 100):
        raise HTTPException(status_code=429, detail="User TPM limit exceeded")
    if not concurrency_acquire(RedisKeys.concurrency_tenant(tenant_id), conc_limit_tenant):
        raise HTTPException(status_code=429, detail="Tenant concurrency limit exceeded")
    if not concurrency_acquire(RedisKeys.concurrency_user(tenant_id, user_id), conc_limit_user):
        release_concurrency(RedisKeys.concurrency_tenant(tenant_id))
        raise HTTPException(status_code=429, detail="User concurrency limit exceeded")
    
    try:
        provider = get_provider(request.model)
        result = await db.execute(
            select(TenantAPIKey).where(
                TenantAPIKey.tenant_id == current_user.tenant_id,
                TenantAPIKey.provider == provider
            )
        )
        tenant_key = result.scalars().first()
        if not tenant_key:
            raise HTTPException(
                status_code=400,
                detail=f"No {provider} API Key registered for your organization"
            )
        
        api_key = decrypt_api_key(tenant_key.encrypted_key)
        if provider == "openai":
            return await call_openai(api_key, request.model, request.message, PROVIDER_URLS["openai"])
        elif provider == "anthropic":
            return await call_anthropic(api_key, request.model, request.message)
        elif provider == "gemini":
            return await call_gemini(api_key, request.model, request.message)
        elif provider in ["groq", "mistral"]:
            return await call_openai(api_key, request.model, request.message, url=PROVIDER_URLS[provider])
        elif provider == "cohere":
            return await call_cohere(api_key, request.model, request.message)
    finally:
        release_concurrency(RedisKeys.concurrency_tenant(tenant_id))
        release_concurrency(RedisKeys.concurrency_user(tenant_id, user_id))