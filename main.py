from fastapi import FastAPI
from app.routers import auth, tenant, keys, chat, stat
from app.database import init_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="1keycore",
              docs_url=None,
              redoc_url=None,
              openapi_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://1keycore.saurabh.codes", "http:1keyapi.saurabh.codes", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def say_Hello():
    return { "message: ", "Hello World1"}

@app.on_event("startup")
async def on_startup():
    """Initialize the database on application startup."""
    await init_db()

app.include_router(auth.router)
app.include_router(tenant.router)
app.include_router(keys.router)
app.include_router(chat.router)
app.include_router(stat.router)
     

