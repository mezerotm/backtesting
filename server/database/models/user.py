"""
User model for authentication and user management.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """User model for authentication and profile data."""

    id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Model for creating a new user."""

    email: EmailStr
    name: str
    password: str


class UserUpdate(BaseModel):
    """Model for updating user data."""

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserLogin(BaseModel):
    """Model for user login."""

    email: EmailStr
    password: str
