from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class AddComponentPayload(BaseModel):
    type: str


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


class MoveComponentOperation(BaseModel):
    """
    Reorder/relocate a component within (or between) containers.

    - `targetId`: the component to move.
    - `targetContainerId`: the container it should end up in. May be the same
      as its current parent (the typical "drag to reorder within a section"
      case). Use the root checklist id to reorder top-level sections.
    - `position`: zero-based index inside the target container's children/items.
      Use a negative index or an index ≥ length to append at the end.
    """
    operation: Literal["moveComponent"]
    targetId: str
    targetContainerId: str
    position: int


ChecklistOperation = Annotated[
    AddComponentOperation | UpdateComponentOperation | DeleteComponentOperation | MoveComponentOperation,
    Field(discriminator="operation"),
]


class ChecklistOperationsPatchRequest(BaseModel):
    operations: list[ChecklistOperation]
