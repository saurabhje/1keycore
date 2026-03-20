from fastapi import HTTPException, Depends, APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.dependencies import get_current_user
from app.models import User, TenantAPIKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.security import decrypt_api_key
import httpx

router = APIRouter(prefix="/chat", tags=["chat"])

PROVIDER_URLS = {
    "openai":    "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "gemini":    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "groq":      "https://api.groq.com/openai/v1/chat/completions",
    "mistral":   "https://api.mistral.ai/v1/chat/completions",
    "cohere":    "https://api.cohere.com/v2/chat",
}

PROVIDER_MODELS = {
    "openai":    ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
    "gemini":    ["gemini-1.5-pro", "gemini-1.5-flash"],
    "groq":      ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
    "mistral":   ["mistral-large-latest", "mistral-small-latest"],
    "cohere":    ["command-r-plus", "command-r"],
}

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
        return await call_openAI(api_key, request.model, request.message, PROVIDER_URLS["openai"])
    elif provider == "anthropic":
        return await call_anthropic(api_key, request.model, request.message)
    elif provider == "gemini":
        return await call_gemini(api_key, request.model, request.message)
    elif provider in ["groq", "mistral"]:
        return await call_openAI(api_key, request.model, request.message, url=PROVIDER_URLS[provider])
    elif provider == "cohere":
        return await call_cohere(api_key, request.model, request.message)
    

async def call_openAI(api_key: str, model: str, message: str, url: str = PROVIDER_URLS["openai"]) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": message}]
            },
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {
            "response": data["choices"][0]["message"]["content"],
            "model": model
        }

async def call_anthropic(api_key: str, model: str, message: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PROVIDER_URLS["anthropic"],
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": message}]
            },
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {
            "response": data["content"][0]["text"],
            "model": model
        }

async def call_gemini(api_key: str, model: str, message: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = PROVIDER_URLS["gemini"].format(model=model)
        response = await client.post(
            f"{url}?key={api_key}",
            json={
                "contents": [{"parts": [{"text": message}]}]
            },
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {
            "response": data["candidates"][0]["content"]["parts"][0]["text"],
            "model": model
        }

async def call_cohere(api_key: str, model: str, message: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PROVIDER_URLS["cohere"],
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": message}]
            },
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {
            "response": data["message"]["content"][0]["text"],
            "model": model
        }




