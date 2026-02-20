import uuid
from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.timezone.utc.now)

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True, primary_key=True, default=uuid.uuid4))
    email = Column(String, uniuque=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="users")






