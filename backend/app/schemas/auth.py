"""Pydantic schemas for authentication, token exchange, and user profiles."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from backend.app.models.user import UserRole


class RegisterRequest(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = Field(default=UserRole.ADMIN)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: str

    model_config = {
        "from_attributes": True
    }


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    user: UserProfileResponse

