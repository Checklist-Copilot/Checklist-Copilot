from typing import Any

from pydantic import BaseModel


class AiCreateFromTextRequest(BaseModel):
    prompt: str
    title: str | None = None
    description: str | None = None


class AiEditChecklistRequest(BaseModel):
    instruction: str


class AiGenerateRequest(BaseModel):
    prompt: str


class AiObserveChatMessage(BaseModel):
    """One turn of conversation history, kept flat for easy frontend handling."""
    role: str  # "user" | "assistant"
    content: str


class AiObserveRequest(BaseModel):
    """
    Vision request. The image must already exist in storage (uploaded via
    POST /api/files/upload/image) — pass its id here. The frontend keeps the
    running conversation in memory and replays it via `prior_messages` so the
    user can ask follow-up questions about the same image.
    """
    instruction: str
    image_id: Any  # uuid; kept loose so pydantic accepts both string and UUID
    prior_messages: list[AiObserveChatMessage] | None = None


class AiSkippedCall(BaseModel):
    call: dict[str, Any]
    reason: str


class AiResponse(BaseModel):
    """
    Returned by the AI edit endpoint. `checklist` is the resulting JSON tree
    (after all valid tool calls were applied). `reply` is the model's
    natural-language message to the user — the frontend shows this in the chat
    panel. `skipped` lists any tool calls that failed validation so the frontend
    can surface them for debugging.
    """
    checklist: dict[str, Any]
    reply: str
    applied_calls: int
    skipped: list[AiSkippedCall]
