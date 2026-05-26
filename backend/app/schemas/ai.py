from typing import Any

from pydantic import BaseModel


class AiCreateFromTextRequest(BaseModel):
    prompt: str
    title: str | None = None
    description: str | None = None


class AiEditChecklistRequest(BaseModel):
    instruction: str


class AiSkippedCall(BaseModel):
    call: dict[str, Any]
    reason: str


class AiResponse(BaseModel):
    """
    Returned by both AI endpoints. `checklist` is the resulting JSON tree (after
    all valid tool calls were applied). `skipped` lists any tool calls that
    failed validation so the frontend can surface them for debugging.
    """
    checklist: dict[str, Any]
    applied_calls: int
    skipped: list[AiSkippedCall]
