import httpx
from fastapi import HTTPException
from app.helpers.constants import PROVIDER_URLS

async def call_openai(api_key: str, model: str, message: str, url: str = PROVIDER_URLS["openai"]) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": message}]},
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {"response": data["choices"][0]["message"]["content"], "model": model}

async def call_anthropic(api_key: str, model: str, message: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PROVIDER_URLS["anthropic"],
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": model, "max_tokens": 1024, "messages": [{"role": "user", "content": message}]},
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {"response": data["content"][0]["text"], "model": model}

async def call_gemini(api_key: str, model: str, message: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = PROVIDER_URLS["gemini"].format(model=model)
        response = await client.post(
            f"{url}?key={api_key}",
            json={"contents": [{"parts": [{"text": message}]}]},
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {"response": data["candidates"][0]["content"]["parts"][0]["text"], "model": model}

async def call_cohere(api_key: str, model: str, message: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PROVIDER_URLS["cohere"],
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": message}]},
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())
        data = response.json()
        return {"response": data["message"]["content"][0]["text"], "model": model}