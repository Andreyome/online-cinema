from pydantic import BaseModel, EmailStr, constr
from typing import Optional

class RegisterRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8)

class ResendActivationRequest(BaseModel):
    email: EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordConfirmRequest(BaseModel):
    token: str
    new_password: constr(min_length=8)

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: constr(min_length=8)

class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True
