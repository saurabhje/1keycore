from fastapi import HTTPException

from app.database import AsyncSessionLocal
from app.models import RequestLog

async def save_log_request(log_payload: dict):
    async with AsyncSessionLocal() as db:
        try:
            log_entry = RequestLog(**log_payload)
            db.add(log_entry)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save log: {str(e)}")
    
