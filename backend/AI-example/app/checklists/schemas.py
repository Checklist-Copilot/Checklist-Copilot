from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ChecklistCreateRequest(BaseModel):
    title: str
    data: dict[str, Any]


class ChecklistUpdateRequest(BaseModel):
    title: str | None = None
    data: dict[str, Any] | None = None


class ChecklistResponse(BaseModel):
    id: int
    title: str
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
