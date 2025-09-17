from pydantic import BaseModel, EmailStr, constr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com", description="The user's unique email address.")
    password: constr(min_length=8) = Field(..., example="SecurePa$$w0rd",
                                           description="A password of at least 8 characters.")


class ResendActivationRequest(BaseModel):
    email: EmailStr = Field(..., description="The email address of the account to be activated.")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com", description="The user's email address.")
    password: str = Field(..., example="SecurePa$$w0rd", description="The user's password.")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="The short-lived JWT used to access protected endpoints.")
    refresh_token: str = Field(..., description="A long-lived token used to obtain a new access token.")
    token_type: str = Field("bearer", description="The type of the token, typically 'bearer'.")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="The refresh token provided at login.")


class ResetPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="The email address to send the password reset link to.")


class ResetPasswordConfirmRequest(BaseModel):
    token: str
    new_password: constr(min_length=8)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="The user's current password.")
    new_password: constr(min_length=8) = Field(..., description="The new password for the account.")


class UserOut(BaseModel):
    id: int = Field(..., description="The unique ID of the user.")
    email: EmailStr = Field(..., description="The user's email address.")
    is_active: bool = Field(..., description="Indicates whether the user's account is active.")

    class Config:
        from_attributes = True
