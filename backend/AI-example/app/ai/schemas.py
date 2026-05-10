from typing import Any

from pydantic import BaseModel


class AiEditChecklistRequest(BaseModel):
    instruction: str


class AiCreateFromTextRequest(BaseModel):
    text: str


class AiOperation(BaseModel):
    type: str
    target_uid: str | None = None
    payload: dict[str, Any] | None = None


class AiEditResponse(BaseModel):
    operations: list[AiOperation]
    checklist: dict[str, Any]
    explanation: str | None = None


class AiChecklistResponse(BaseModel):
    checklist: dict[str, Any]
    explanation: str | None = None
