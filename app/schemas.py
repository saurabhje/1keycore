from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID

# Tenant schemas
class TenantBase(BaseModel):
    name: str
    
class TenantCreate(TenantBase):
    pass

class TenantResponse(TenantBase):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# User schemas
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str
    tenant_id: UUID

class UserResponse(UserBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)