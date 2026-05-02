from fastapi import HTTPException

from app.database import AsyncSessionLocal
from app.helpers.semanticCache import hash_message
from app.helpers.semanticCache import hash_message
from app.models import RequestLog, SemanticCache

async def save_log_request(log_payload: dict):
    async with AsyncSessionLocal() as db:
        try:
            log_entry = RequestLog(**log_payload)
            db.add(log_entry)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save log: {str(e)}")

async def semantic_save(tenant_id: str, model: str, system_prompt: str, embedding: list[float], response: str):
    sp_hash = hash_message(system_prompt)
    async with AsyncSessionLocal() as db:
        try:
            semantic_entry = SemanticCache(
                tenant_id=tenant_id,
                model=model,
                embedding=embedding,
                system_prompt_hash=sp_hash,
                response=response
            )
            db.add(semantic_entry)
            await db.commit()
        except Exception as e:
            await db.rollback()     
            raise HTTPException(status_code=500, detail=f"Failed to save semantic cache: {str(e)}")