import hashlib
from typing import Optional
import numpy as np
from app.models import SemanticCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import bindparam, select
from pgvector.sqlalchemy import Vector
from huggingface_hub import InferenceClient
from app.config import settings


SEMANTIC_CACHE_DISTANCE_THRESHOLD = 0.15
client = InferenceClient(
    provider="hf-inference",
    api_key=settings.HF_TOKEN
)


EMBEDDING_DIMENSION = 384

def _coerce_embedding(embedding: np.ndarray) -> list[float]:
    if embedding.shape[0] != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Expected {EMBEDDING_DIMENSION}, got {embedding.shape[0]}"
        )

    return embedding.astype(np.float32).tolist()

async def get_embeddings(text: str) -> list[float]:
    result = client.feature_extraction(
        text,
        model="BAAI/bge-small-en"
    )

    embedding = np.asarray(result)

    return _coerce_embedding(embedding)


def hash_message(system_prompt: str | None) -> Optional[str]:
    if not system_prompt:
        return None
    return hashlib.sha256(system_prompt.strip().encode()).hexdigest()

async def get_semantic_cache(
        db: AsyncSession, 
        tenant_id: str, 
        model: str,
        system_prompt: str | None, 
        embedding: list[float]
) -> str | None:
    sp_hash = hash_message(system_prompt)

    query_embedding = bindparam(
        "query_embedding",
        value=embedding,
        type_=Vector(EMBEDDING_DIMENSION)
    )

    distance = SemanticCache.embedding.cosine_distance(query_embedding)

    results = await db.execute(
        select(SemanticCache).where(
            SemanticCache.tenant_id == tenant_id,
            SemanticCache.model == model,
            SemanticCache.system_prompt_hash == sp_hash,
            distance < SEMANTIC_CACHE_DISTANCE_THRESHOLD
        ).order_by(distance)
    )

    row = results.scalars().first()
    return row.response if row else None

async def set_semantic_cache(
        db: AsyncSession, 
        tenant_id: str, 
        model: str,
        system_prompt: str | None, 
        embedding: list[float],
        response: str
):
    sp_hash = hash_message(system_prompt)

    cache_entry = SemanticCache(
        tenant_id=tenant_id,
        model=model,
        embedding=embedding,
        system_prompt_hash=sp_hash,
        response=response
    )
    db.add(cache_entry)
    await db.commit()
