from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

# Tenant schemas
class TenantBase(BaseModel):
    name: str
    
class TenantCreate(TenantBase):
    name: str
    slug: str

class TenantResponse(TenantBase):
    id: UUID
    slug: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TenantOnBoarding(BaseModel):
    tenant: TenantResponse
    access_token: str
    token_type: str = "bearer"

class JoinTenant(BaseModel):
    invite_code: str

# User schemas
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    name: str
    password: str

class UserResponse(UserBase):
    id: UUID
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

class APIKeyCreateResponse(BaseModel):
    api_key: str

class APIKeyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    provider: str
    req_key: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ChatRequest(BaseModel):
    message: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    # extra_params: Optional[dict[str, Any]] = None
    best_model_choice: bool = True
    model: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    model: str
    cached: bool = False
    raw_data: Optional[dict[str, Any]] = None