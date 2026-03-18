from fastapi import FastAPI
from app.routers import auth, tenant, keys, chat
from app.database import init_db


app = FastAPI(title="gatewise")

@app.on_event("startup")
async def on_startup():
    """Initialize the database on application startup."""
    await init_db()

app.include_router(auth.router)
app.include_router(tenant.router)
app.include_router(keys.router)
app.include_router(chat.router)
     

