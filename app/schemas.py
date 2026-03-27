from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

# Tenant schemas
class TenantBase(BaseModel):
    name: str
    
class TenantCreate(TenantBase):
    name: str

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

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class APIKeyCreate(BaseModel):
    provider: str
    api_key: str

class APIKeyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    provider: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ChatRequest(BaseModel):
    message: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    # extra_params: Optional[dict[str, Any]] = None
    model: str

class ChatResponse(BaseModel):
    response: str
    model: str