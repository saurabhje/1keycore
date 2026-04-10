from fastapi import FastAPI
from app.routers import auth, tenant, keys, chat
from app.database import init_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="gatewise")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    """Initialize the database on application startup."""
    await init_db()

app.include_router(auth.router)
app.include_router(tenant.router)
app.include_router(keys.router)
app.include_router(chat.router)
     

