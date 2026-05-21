import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileBase(BaseModel):
    file_type: str
    file_name: str


class FileCreate(FileBase):
    pass


class FileRead(FileBase):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class FileUploadResponse(FileRead):
    pass


class FileDeleteResponse(BaseModel):
    message: str
