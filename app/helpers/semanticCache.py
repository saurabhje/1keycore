import hashlib
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from app.models import SemanticCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import bindparam, select
from pgvector.sqlalchemy import Vector

sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

EMBEDDING_DIMENSION = 384
SEMANTIC_CACHE_DISTANCE_THRESHOLD = 0.25


def _coerce_embedding(raw_embedding: list[float]) -> list[float]:
    embedding = np.asarray(raw_embedding, dtype=np.float32).reshape(-1)
    if embedding.size != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Expected embedding dimension {EMBEDDING_DIMENSION}, got {embedding.size}"
        )
    return embedding.tolist()


def get_embeddings(text: str) -> list[float]:
    raw_embedding = sentence_model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    return _coerce_embedding(raw_embedding)


def hash_message(system_prompt: str | None) -> Optional[str]:
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
        message: str, 
        response: str
):
    embedding = get_embeddings(message)
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
