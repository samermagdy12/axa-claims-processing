from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8)
    national_id: str = Field(min_length=1, max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    policy_id: str
    policy_number: str
    product_line: str
    status: str
    start_date: date
    end_date: date
    annual_limit: Decimal
    remaining_limit: Decimal
    deductible: Decimal
    riders: list[str]
