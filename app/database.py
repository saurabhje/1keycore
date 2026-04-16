import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from .config import settings

engine: AsyncEngine = create_async_engine(settings.DB_URL, echo=False, future=True, pool_pre_ping=True)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
	"""Yield an async SQLAlchemy session for FastAPI dependencies."""
	async with AsyncSessionLocal() as session:
		yield session


async def init_db() -> None:
	"""Create tables from ORM metadata. Use Alembic for production migrations."""
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)


async def set_tenant_for_session(session: AsyncSession, tenant_id: Optional[int]) -> None:
	"""Set a per-transaction Postgres setting to the current tenant.

	Useful when using Row Level Security policies that reference
	`current_setting('app.current_tenant')::int`.
	Call early in a request transaction (e.g., middleware or repo helper).
	"""
	if tenant_id is None:
		return
	await session.execute(text("SET LOCAL app.current_tenant = :t").bindparams(t=str(tenant_id)))

