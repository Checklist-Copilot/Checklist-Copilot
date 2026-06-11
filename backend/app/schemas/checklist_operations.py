from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AddComponentPayload(BaseModel):
    # Keep optional per-component fields such as humanReadableId, children,
    # items, value, required, etc. The specific add handlers validate those
    # fields by component type.
    model_config = ConfigDict(extra="allow")

    type: str
    label: str


class AddComponentOperation(BaseModel):
    operation: Literal["addComponent"]
    targetContainerId: str
    position: str | dict[str, Any] = "end"
    component: AddComponentPayload | dict[str, Any]


class UpdateComponentOperation(BaseModel):
    operation: Literal["updateComponent"]
    targetId: str
    patch: dict[str, Any]


class DeleteComponentOperation(BaseModel):
    operation: Literal["deleteComponent"]
    targetId: str


ChecklistOperation = Annotated[
    AddComponentOperation | UpdateComponentOperation | DeleteComponentOperation,
    Field(discriminator="operation"),
]


class ChecklistOperationsPatchRequest(BaseModel):
    operations: list[ChecklistOperation]
