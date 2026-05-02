from fastapi import HTTPException, Depends, APIRouter, BackgroundTasks
import time
from app.helpers.tokens import count_tokens, extract_tokens
from app.schemas import ChatRequest, ChatResponse
from app.dependencies import chat_user
from app.models import User, TenantAPIKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.security import decrypt_api_key
from app.helpers.rate_limiter import check_rpm_token_bucket, check_tpm, concurrency_acquire, release_concurrency, safe_decr
from app.helpers.redis_keys import RedisKeys
from app.helpers.constants import DEFAULT_MAX_TOKENS, PROVIDER_MODELS, PROVIDER_URLS
from app.helpers.providers import call_anthropic, call_cohere, call_gemini, call_openai
from app.helpers.cache import create_key, get_cache, set_cache
from app.helpers.semanticCache import get_embeddings, get_semantic_cache
from app.helpers.modelRouter import get_best_model, score_complexity
from app.helpers.task import save_log_request, semantic_save

router = APIRouter(prefix="/chat", tags=["chat"])
user_rpm = 20
tenant_rpm = 2000
conc_limit_user = 4
conc_limit_tenant = 20
tpm_limit_user = 1000000
tpm_limit_tenant = 1000000

def get_provider(model: str) -> str:
    for provider, models in PROVIDER_MODELS.items():
        if model in models:
            return provider
    raise HTTPException(status_code=400, detail=f"Unknown model '{model}'. Check supported models.")

@router.post("/", response_model=ChatResponse)
async def chat(
        request: ChatRequest,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(chat_user),
        db: AsyncSession = Depends(get_session)
):
    user_id = str(current_user.id)
    tenant_id = str(current_user.tenant_id)
    input_token = count_tokens(request.message, request.system_prompt)
    estimated_output_token = request.max_tokens or DEFAULT_MAX_TOKENS
    total_token = input_token + estimated_output_token
    start_time = time.perf_counter()

    if not check_rpm_token_bucket(RedisKeys.rpm_user(tenant_id, user_id), user_rpm):
        raise HTTPException(status_code=429, detail="User RPM limit exceeded")
    if not check_rpm_token_bucket(RedisKeys.rpm_tenant(tenant_id), tenant_rpm):
        raise HTTPException(status_code=429, detail="Tenant RPM limit exceeded")
    if not check_tpm(RedisKeys.tpm_user(tenant_id, user_id), tpm_limit_user, total_token):
        raise HTTPException(status_code=429, detail="User TPM limit exceeded")
    if not check_tpm(RedisKeys.tpm_tenant(tenant_id), tpm_limit_tenant, total_token):
        raise HTTPException(status_code=429, detail="Tenant TPM limit exceeded")
    if not concurrency_acquire(RedisKeys.concurrency_tenant(tenant_id), conc_limit_tenant):
        raise HTTPException(status_code=429, detail="Tenant concurrency limit exceeded")
    if not concurrency_acquire(RedisKeys.concurrency_user(tenant_id, user_id), conc_limit_user):
        release_concurrency(RedisKeys.concurrency_tenant(tenant_id))
        raise HTTPException(status_code=429, detail="User concurrency limit exceeded")
    
    try:
        should_cache = request.temperature is None or request.temperature == 0.0

        result = await db.execute(
            select(TenantAPIKey.encrypted_key, TenantAPIKey.provider).where(
                TenantAPIKey.tenant_id == current_user.tenant_id,
            )
        )
        rows = result.fetchall()
        available_providers = [row.provider for row in rows]
        tenant_keys = {row.provider: row.encrypted_key for row in rows}
        if not available_providers:
            raise HTTPException(status_code=400, detail="Please add at least one API key.")
    
        log_tier =  None, None
        if request.best_model_choice:
            log_tier = tier = score_complexity(request.message, request.system_prompt)
            request.model = get_best_model(available_providers, tier)
    

        elif not request.model:
            raise HTTPException(status_code=400, detail="Model must be specified if best_model_choice is false.")
        
        cache_key = None
        cache_type = None
        cache_success = False
        embedding = await get_embeddings(request.message)
        if should_cache:
            cache_key = create_key(tenant_id, request.model, request.message, request.max_tokens or DEFAULT_MAX_TOKENS, request.temperature or 0.0)
            cached_response = get_cache(cache_key)
            if cached_response:
                cache_success = True
                cache_type = "exact"
                return {"response": cached_response, "model": request.model, "cached": True}
            semantic_response = await get_semantic_cache(db, tenant_id, request.model, request.system_prompt, embedding)
            if semantic_response:
                cache_success = True
                cache_type = "semantic"
                return {"response": semantic_response, "model": request.model, "cached": True}
            

        provider = get_provider(request.model)
        use_key = tenant_keys.get(provider)
        if not use_key:
            raise HTTPException(
                status_code=400,
                detail=f"No {provider} API Key registered for your organization"
            )
        
        api_key = decrypt_api_key(use_key)
        outbound_start_time = time.perf_counter()
        if provider == "openai":
            llm_response =  await call_openai(api_key, request, url=PROVIDER_URLS["openai"])
        elif provider == "anthropic":
            llm_response =  await call_anthropic(api_key, request)
        elif provider == "gemini":
            llm_response =  await call_gemini(api_key, request)
        elif provider in ["groq", "mistral"]:
            llm_response =  await call_openai(api_key, request, url=PROVIDER_URLS[provider])
        elif provider == "cohere":
            llm_response =  await call_cohere(api_key, request)

        provider_latency_ms = int((time.perf_counter() - outbound_start_time) * 1000)

        exact_token = extract_tokens(llm_response["raw_data"], provider)
        if exact_token <= 0:
            exact_token = total_token
        log_token = exact_token if not cache_success else 0
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        gateway_latency_ms = latency_ms - provider_latency_ms
        log_payload = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "model": request.model,
            "tier": log_tier,
            "latency_ms": gateway_latency_ms,
            "cache_success": cache_success,
            "cache_type": cache_type,
            "tokens_used": log_token,
        }

        background_tasks.add_task(save_log_request, log_payload)

        delta = exact_token - total_token
        tenant_tpm_key = RedisKeys.tpm_tenant(tenant_id)
        user_tpm_key = RedisKeys.tpm_user(tenant_id, user_id)

        if delta > 0:
            check_tpm(tenant_tpm_key, tpm_limit_tenant, delta)
            check_tpm(user_tpm_key, tpm_limit_user, delta)
        elif delta < 0:
            safe_decr(tenant_tpm_key, -delta)
            safe_decr(user_tpm_key, -delta)
        
            
        if should_cache:
            set_cache(cache_key, llm_response["response"])
            background_tasks.add_task(semantic_save, tenant_id, request.model, request.system_prompt, embedding, llm_response["response"])
        return {
            "response": llm_response["response"], 
            "model": request.model, 
            "cached":  cache_success,
            "latency_ms": gateway_latency_ms,
            "tokens": log_token
}
    finally:
        release_concurrency(RedisKeys.concurrency_tenant(tenant_id))
        release_concurrency(RedisKeys.concurrency_user(tenant_id, user_id))