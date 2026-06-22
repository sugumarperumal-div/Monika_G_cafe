import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.models.database import get_db
from backend.models.models import User, PasswordReset as PasswordResetModel, OTPVerification
from backend.schemas.schemas import UserRegister, UserLogin, TokenResponse, PasswordReset, OTPRequest, OTPVerify
from backend.utils.auth import hash_password, verify_password, create_access_token, get_current_user
from backend.utils.notifications import send_password_reset_email, generate_otp, send_otp_sms, otp_expiry
from backend.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role.name,
        "loyalty_points": user.loyalty_points,
        "profile_image": user.profile_image,
    }


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role_id=4,  # customer
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=_user_to_dict(user))


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email, User.is_active == True).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=_user_to_dict(user))


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return _user_to_dict(current_user)


@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Return success regardless to prevent email enumeration
        return {"message": "If this email exists, a reset link has been sent"}
    token = secrets.token_urlsafe(32)
    reset = PasswordResetModel(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(reset)
    db.commit()
    send_password_reset_email(user.email, token)
    return {"message": "Password reset email sent"}


@router.post("/reset-password")
def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    reset = db.query(PasswordResetModel).filter(
        PasswordResetModel.token == data.token,
        PasswordResetModel.used == False,
        PasswordResetModel.expires_at > datetime.utcnow(),
    ).first()
    if not reset:
        raise HTTPException(400, "Invalid or expired token")
    user = db.query(User).filter(User.id == reset.user_id).first()
    user.password_hash = hash_password(data.new_password)
    reset.used = True
    db.commit()
    return {"message": "Password reset successfully"}


@router.post("/send-otp")
def send_otp(data: OTPRequest, db: Session = Depends(get_db)):
    otp = generate_otp()
    record = OTPVerification(
        phone=data.phone,
        otp=otp,
        purpose=data.purpose,
        expires_at=otp_expiry(),
    )
    db.add(record)
    db.commit()
    sent = send_otp_sms(data.phone, otp)
    return {"message": "OTP sent" if sent else "OTP generated (SMS delivery pending)", "debug_otp": otp if settings.DEBUG else None}


@router.post("/verify-otp")
def verify_otp(data: OTPVerify, db: Session = Depends(get_db)):
    record = db.query(OTPVerification).filter(
        OTPVerification.phone == data.phone,
        OTPVerification.otp == data.otp,
        OTPVerification.verified == False,
        OTPVerification.expires_at > datetime.utcnow(),
    ).order_by(OTPVerification.created_at.desc()).first()
    if not record:
        raise HTTPException(400, "Invalid or expired OTP")
    record.verified = True
    db.commit()
    return {"message": "OTP verified"}


@router.get("/google")
def google_login():
    """Redirect user to Google OAuth consent screen."""
    from authlib.integrations.httpx_client import AsyncOAuth2Client
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
    )
    from fastapi.responses import RedirectResponse
    return RedirectResponse(google_auth_url)


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback, create/login user."""
    import httpx
    async with httpx.AsyncClient() as client:
        token_resp = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        token_data = token_resp.json()
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        google_user = user_resp.json()

    user = db.query(User).filter(User.email == google_user["email"]).first()
    if not user:
        user = User(
            name=google_user.get("name", ""),
            email=google_user["email"],
            google_id=google_user["id"],
            profile_image=google_user.get("picture"),
            password_hash=hash_password(secrets.token_hex(16)),
            role_id=4,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=_user_to_dict(user))