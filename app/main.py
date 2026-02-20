from fastapi import FastAPI
from .database import init_db

app = FastAPI(title="Multi-Tenant SaaS API")

@app.on_event("startup")
async def on_startup():
    """Initialize the database on application startup."""
    await init_db()
     