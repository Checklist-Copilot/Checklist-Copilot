import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import (
    UserCreateRequest,
    UserCreateResponse,
    UserDeleteResponse,
    UserGetResponse,
    UserListResponse,
    UserResponse,
)
from app.services.auth import issue_token_for_user
from app.services.users import create_user, delete_user, get_user_by_id, list_users


router = APIRouter(prefix="/users")


@router.post("/create", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
def create_user_route(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserCreateResponse:
    try:
        user = create_user(db, payload)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    return UserCreateResponse(
        **UserResponse.model_validate(user).model_dump(),
        access_token=issue_token_for_user(user),
    )


@router.get("", response_model=UserListResponse)
def list_users_route(db: Session = Depends(get_db)) -> UserListResponse:
    users = list_users(db)
    return UserListResponse(users=[UserResponse.model_validate(user) for user in users])


@router.get("/{user_id}", response_model=UserGetResponse)
def get_user_route(user_id: uuid.UUID, db: Session = Depends(get_db)) -> UserGetResponse:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return UserGetResponse.model_validate(user)


@router.delete("/delete/{user_id}", response_model=UserDeleteResponse)
def delete_user_route(user_id: uuid.UUID, db: Session = Depends(get_db)) -> UserDeleteResponse:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    delete_user(db, user)
    return UserDeleteResponse(message="User deleted successfully.")
