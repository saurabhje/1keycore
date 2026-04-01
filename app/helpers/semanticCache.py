import hashlib
from sentence_transformers import SentenceTransformer
from app.models import SemanticCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    
def get_embeddings(text: str) -> list:
    return sentence_model.encode(text).tolist()

def hash_message(system_prompt: str | None) -> str:
    if not system_prompt:
        return None
    return hashlib.sha256(system_prompt.strip().encode()).hexdigest()

async def get_semantic_cache(
        db: AsyncSession, 
        tenant_id: str, 
        model: str,
        system_prompt: str | None, 
        message: str
) -> str | None:
    
    embedding = get_embeddings(message)
    sp_hash = hash_message(system_prompt)
    
    results = await db.execute(
        select(SemanticCache).where(
            SemanticCache.tenant_id == tenant_id,
            SemanticCache.model == model,
            SemanticCache.system_prompt_hash == sp_hash,
            SemanticCache.embedding.op("<->")(embedding) < 0.85
        )
    )

    row = results.scalars().first()
    return row.response if row else None

async def set_semantic_cache(
        db: AsyncSession, 
        tenant_id: str, 
        model: str,
        system_prompt: str | None, 
        message: str, 
        response: str
):
    embedding = get_embeddings(message)
    sp_hash = hash_message(system_prompt)

    cache_entry = SemanticCache(
        tenant_id=tenant_id,
        model=model,
        system_prompt_hash=sp_hash,
        query=message,
        embedding=embedding,
        response=response
    )
    db.add(cache_entry)
    await db.commit()
