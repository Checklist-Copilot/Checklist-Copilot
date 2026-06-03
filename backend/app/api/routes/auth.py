from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import AuthResponse, ChangePasswordRequest, CurrentUserUpdateRequest, LoginRequest
from app.schemas.user import UserResponse
from app.services.auth import authenticate_user, get_current_user, issue_token_for_user


router = APIRouter(prefix="/auth")


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = authenticate_user(db, str(payload.email), payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    token = issue_token_for_user(user)
    return AuthResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def read_me(current_user=Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: CurrentUserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    existing_user = db.scalar(
        select(User).where(User.email == str(payload.email), User.id != current_user.id)
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    username = payload.username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username cannot be empty.",
        )

    current_user.username = username
    current_user.email = str(payload.email)
    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.patch("/me/password", response_model=UserResponse)
def change_me_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    if not payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password cannot be empty.",
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)
