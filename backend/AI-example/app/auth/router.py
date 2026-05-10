from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.schemas import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from app.auth.service import (
    register_user,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.db.models import User
from app.db.session import get_db


router = APIRouter()


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = register_user(db, payload.email, payload.password)
    token = create_access_token(user.id)
    return AuthResponse(access_token=token)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    token = create_access_token(user.id)
    return AuthResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
