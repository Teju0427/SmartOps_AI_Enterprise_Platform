from __future__ import annotations

import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import RefreshToken, User
from app.schemas.auth import (
    AccessTokenResponse,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRead,
    UserRegister,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _issue_tokens(db: Session, user: User, request: Request | None = None) -> TokenResponse:
    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    raw_refresh, refresh_hash = create_refresh_token(subject=str(user.id))

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=request.headers.get("user-agent") if request else None,
        ip_address=request.client.host if request and request.client else None,
    ))
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh, user=UserRead.model_validate(user))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Annotated[Session, Depends(get_db)]) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        department=payload.department,
        region=payload.region,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been deactivated.")

    return _issue_tokens(db, user, request)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_access_token(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> AccessTokenResponse:
    from app.core.security import pwd_context

    candidates = db.query(RefreshToken).filter(
        RefreshToken.revoked.is_(False),
        RefreshToken.expires_at > datetime.now(timezone.utc),
    ).all()

    matched = next((c for c in candidates if pwd_context.verify(payload.refresh_token, c.token_hash)), None)
    if matched is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

    user = db.query(User).filter(User.id == matched.user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active.")

    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> None:
    from app.core.security import pwd_context

    candidates = db.query(RefreshToken).filter(RefreshToken.revoked.is_(False)).all()
    matched = next((c for c in candidates if pwd_context.verify(payload.refresh_token, c.token_hash)), None)
    if matched:
        matched.revoked = True
        db.commit()


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser) -> User:
    return current_user
