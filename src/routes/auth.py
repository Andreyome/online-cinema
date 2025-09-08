from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user import PasswordResetToken, User
from src.database.session import get_db
from src.deps import get_current_user
from src.schemas import auth as schemas
from src.crud import auth as crud
# from src.emailer import send_email
from src.schemas.auth import ChangePasswordRequest
from src.utils.hash import verify_password, hash_password
from src.utils.jwt import create_access_token, create_refresh_token, decode_token
from datetime import timedelta
from src.config.settings import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserOut)
async def register(payload: schemas.RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await crud.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await crud.create_user(db, email=payload.email, password=payload.password)
    at = await crud.create_activation_token(db, user)
    link = f"https://your-frontend/activate?token={at.token}"
    # await send_email(user.email, "Activate your account", f"Click to activate: {link}")
    return user

@router.get("/activate")
async def activate(token: str, db: AsyncSession = Depends(get_db)):
    user = await crud.verify_activation_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    return {"detail": "Account activated"}

@router.post("/resend-activation")
async def resend_activation(payload: schemas.ResendActivationRequest, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_email(db, payload.email)
    if not user:
        return {"detail": "If the email is registered, activation email was sent"}
    if user.is_active:
        return {"detail": "Account already active"}
    at = await crud.create_activation_token(db, user)
    link = f"https://your-frontend/activate?token={at.token}"
    # await send_email(user.email, "Activate your account", f"Click to activate: {link}")
    return {"detail": "Activation email sent"}

@router.post("/login", response_model=schemas.TokenResponse)
async def login(payload: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not activated")
    access_payload = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(access_payload)
    rt= await crud.create_refresh_token(db, user.id)
    return {"access_token": access_token, "refresh_token": rt.token, "token_type": "bearer"}

@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh(payload: schemas.RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_row = await crud.get_refresh_token(db, payload.refresh_token)
    if not token_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if token_row.expires_at < __import__("datetime").datetime.utcnow():
        await crud.revoke_refresh_token(db, token_row.token)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    access_payload = {"user_id": token_row.user_id}
    access_token = create_access_token(access_payload)
    return {"access_token": access_token, "refresh_token": token_row.token, "token_type": "bearer"}

@router.post("/logout")
async def logout(payload: schemas.RefreshRequest, db: AsyncSession = Depends(get_db)):
    await crud.revoke_refresh_token(db, payload.refresh_token)
    return {"detail": "Logged out"}

@router.post("/forgot-password")
async def forgot_password(payload: schemas.ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_email(db, payload.email)
    if not user or not user.is_active:
        return {"detail": "If the email is registered, a reset link was sent"}
    pr = await crud.create_password_reset_token(db, user)
    link = f"https://your-frontend/reset-password?token={pr.token}"
    # await send_email(user.email, "Reset your password", f"Click to reset: {link}")
    return {"detail": "If the email is registered, a reset link was sent"}

@router.post("/reset-password")
async def reset_password(payload: schemas.ResetPasswordConfirmRequest, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token == payload.token))
    pr = q.scalars().first()
    if not pr or pr.expires_at < __import__("datetime").datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    user_q = await db.execute(select(User).where(User.id == pr.user_id))
    user = user_q.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    user.hashed_password = hash_password(payload.new_password)
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    await db.commit()
    return {"detail": "Password updated"}

@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from src.utils.hash import verify_password, hash_password
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    return {"detail": "Password changed"}
