import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreateRequest(UserBase):
    password: str


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDeleteResponse(BaseModel):
    message: str


class UserListResponse(BaseModel):
    users: list[UserResponse]


class UserCreateResponse(UserResponse):
    access_token: str
    token_type: str = "bearer"


class UserGetResponse(UserResponse):
    pass
