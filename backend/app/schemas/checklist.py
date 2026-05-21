import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ChecklistBase(BaseModel):
    title: str
    description: str | None = None
    checklist: dict[str, Any]


class ChecklistCreateRequest(ChecklistBase):
    pass


class ChecklistUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    checklist: dict[str, Any]


class ChecklistResponse(ChecklistBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    checklist_prev: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class ChecklistSummaryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChecklistCreateResponse(ChecklistResponse):
    pass


class ChecklistUpdateResponse(ChecklistResponse):
    pass


class ChecklistGetResponse(ChecklistResponse):
    pass


class ChecklistListResponse(BaseModel):
    checklists: list[ChecklistSummaryResponse]


class ChecklistDeleteResponse(BaseModel):
    message: str
