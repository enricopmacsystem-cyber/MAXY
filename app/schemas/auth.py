from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=1)


class UserProfile(BaseModel):
    user_id: str
    username: str
    display_name: str
    roles: list[str]
    permissions: list[str]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class SessionInfo(BaseModel):
    session_id: UUID
    user: UserProfile
    expires_at: datetime
    last_activity: datetime
