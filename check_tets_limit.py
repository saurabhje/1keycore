import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8000"


async def send_request(client, headers):
    response = await client.post(f"{BASE_URL}/chat/", json={
            "message": "say hi",
            "model": "llama-3.3-70b-versatile"        
        }, headers=headers, timeout=60.0)
    return response.status_code, response.text

async def test():
    # login first
    login = httpx.post(f"{BASE_URL}/auth/login", json={
        "email": "string@abccorp.com",
        "password": "string"
    })
    if(login.status_code!=200): print("Login error")
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # fire requests rapidly
    async with httpx.AsyncClient() as client:
        tasks = [send_request(client, headers) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        for i, (status, text) in enumerate(results):
            print(f"{i} : {status} -> {text}")

asyncio.run(test())