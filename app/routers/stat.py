from fastapi import APIRouter,Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, desc, case
from app.database import get_session
from app.models import RequestLog, TenantAPIKey, User
from app.dependencies import get_current_user

router = APIRouter(prefix="/usage", tags=["usage"])

BLENDED_TOKEN_COST = 0.000015

@router.get("/summary")
async def get_usage_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    tid = current_user.tenant_id
    keys_result = await db.execute(
        select(func.count(TenantAPIKey.id)).where(TenantAPIKey.tenant_id == tid)
    )
    active_keys = keys_result.scalar() or 0

    stats_query = select(
        func.count(RequestLog.id).label("total_requests"),
        func.sum(RequestLog.tokens_used).label("total_tokens"),
        func.sum(
            case(RequestLog.cache_success, [(True, 0)], else_=0)
        ).label("cache_hits")
    ).where(RequestLog.tenant_id == tid)

    result = await db.execute(stats_query)
    row = result.fetchall()

    total_req = row.total_requests or 0
    total_tokens = row.total_tokens or 0
    cache_hits = row.cache_hits or 0

    hit_rate = (cache_hits / total_req * 100) if total_req > 0 else 0
    estimated_cost = total_tokens * BLENDED_TOKEN_COST

    avg_token_per_req = (total_tokens / total_req) if total_req > 0 else 0
    est_savings = cache_hits * avg_token_per_req * BLENDED_TOKEN_COST

    return {
        "total_requests": total_req,
        "total_tokens": total_tokens,
        "cache_hit_rate": round(hit_rate, 2),
        "estimated_cost_usd": round(estimated_cost, 4),
        "estimated_savings_usd": round(est_savings, 4),
        "active_api_keys": active_keys
    }

@router.get("/by-model")
async def get_usage_by_model(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    tid = current_user.tenant_id
    model_stats_query = select(
        RequestLog.model,
        func.count(RequestLog.id).label("requests"),
        func.sum(RequestLog.tokens_used).label("tokens"),
        func.avg(RequestLog.latency_ms).label("avg_latency_ms"
    ).where(RequestLog.tenant_id == tid).group_by(RequestLog.model).order_by(desc("tokens"))
    )
    result = await db.execute(model_stats_query)
    rows = result.fetchall()

    return [
        {
            "model": row.model,
            "requests": row.requests,
            "tokens": row.tokens,
            "avg_latency_ms": row.avg_latency_ms,
            "estimated_cost_usd" : (row.tokens or 0) * BLENDED_TOKEN_COST
        }
        for row in rows
    ]

@router.get("/by-user")
async def get_usage_by_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    user_stats_query = select(
        User.email,
        RequestLog.user_id,
        func.count(RequestLog.id).label("requests"),
        func.sum(RequestLog.tokens_used).label("tokens"),
    ).join(User, User.id == RequestLog.user_id
           ).where(RequestLog.tenant_id == current_user.tenant_id
            ).group_by(User.email, RequestLog.user_id
            ).order_by(desc("tokens"))
    result = await db.execute(user_stats_query)
    rows = result.fetchall()

    return [
        {
            "email": row.email,
            "user_id": row.user_id,
            "requests": row.requests,
            "tokens": row.tokens,
            "estimated_cost_usd" : (row.tokens or 0) * BLENDED_TOKEN_COST
        }
        for row in rows
    ]

@router.get("/logs")
async def get_recent_logs(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    query = select(
        RequestLog.created_at,
        RequestLog.model,
        RequestLog.tokens_used,
        RequestLog.latency_ms,
        RequestLog.cache_success,
        RequestLog.cache_type
    ).where(RequestLog.tenant_id == current_user.tenant_id
    ).order_by(desc(RequestLog.created_at_)).limit(limit)

    result = await db.execute(query)
    rows = result.fetchall() 

    return [
        {
            "created_at": row.created_at,
            "model": row.model,
            "tokens_used": row.tokens_used,
            "latency_ms": row.latency_ms,
            "cache_success": row.cache_success,
            "cache_type": row.cache_type,
            "estimated_cost_usd": (row.tokens_used or 0) * BLENDED_TOKEN_COST
        }
        for row in rows
    ]