import httpx
from fastapi import HTTPException
from app.helpers.constants import PROVIDER_URLS
from app.schemas import ChatRequest



async def call_openai(api_key: str, req: ChatRequest, url: str = PROVIDER_URLS["openai"]) -> dict:
    payload = {
        "model": req.model,
        "messages": [{"role": "user", "content": req.message}],
        "temperature": req.temperature or 0.7,
        "max_tokens": req.max_tokens or 1000
    }
    # if req.extra_params:
    #     payload.update(req.extra_params)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {"response": data["choices"][0]["message"]["content"], "model": req.model}

async def call_anthropic(api_key: str, req: ChatRequest) -> dict:
    payload = {
        "model": req.model,
        "max_tokens": req.max_tokens or 1024,
        "messages": [{"role": "user", "content": req.message}],
        "temperature": req.temperature or 0.7
    }
    # if req.extra_params:
    #     payload.update(req.extra_params)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PROVIDER_URLS["anthropic"],
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json=payload,
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {"response": data["content"][0]["text"], "model": req.model}

async def call_gemini(api_key: str, req: ChatRequest) -> dict:
    payload = {
        "contents": [{"parts": [{"text": req.message}]}],
        "generationConfig": {
            "temperature": req.temperature or 0.7,
            "maxOutputTokens": req.max_tokens or 1000
        }
    }
    # if req.extra_params:
    #     payload["generationConfig"].update(req.extra_params)
    async with httpx.AsyncClient() as client:
        url = PROVIDER_URLS["gemini"].format(model=req.model)
        response = await client.post(
            f"{url}?key={api_key}",
            json=payload,
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {"response": data["candidates"][0]["content"]["parts"][0]["text"], "model": req.model}

async def call_cohere(api_key: str, req: ChatRequest) -> dict:
    payload = {
        "model": req.model,
        "messages": [{"role": "user", "content": req.message}],
        "temperature": req.temperature or 0.7,
        "max_tokens": req.max_tokens or 1000
    }
    # if req.extra_params:
    #     payload.update(req.extra_params)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PROVIDER_URLS["cohere"],
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {"response": data["message"]["content"][0]["text"], "model": req.model}