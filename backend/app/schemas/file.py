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
    checklist_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class FileUploadResponse(FileRead):
    # Ready-to-use URL for the uploaded file. The route fills this in as
    # `/api/files/<id>/raw`. The frontend can drop it straight into an
    # `imageBlock.images[].url` field; the GET endpoint streams the bytes
    # back from Supabase Storage with the right Content-Type.
    url: str


class FileDeleteResponse(BaseModel):
    message: str
