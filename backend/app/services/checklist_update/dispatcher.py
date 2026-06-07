from app.schemas.checklist_operations import (
    AddComponentOperation,
    ChecklistOperation,
    DeleteComponentOperation,
    MoveComponentOperation,
    UpdateComponentOperation,
)
from app.services.checklist_update.add.dispatcher import dispatch_add_component
from app.services.checklist_update.delete.dispatcher import dispatch_delete_component
from app.services.checklist_update.exceptions import UnsupportedOperationError
from app.services.checklist_update.tree_utils import move_component
from app.services.checklist_update.update.dispatcher import dispatch_update_component


def dispatch_operation(checklist: dict, operation: ChecklistOperation) -> dict:
    if isinstance(operation, AddComponentOperation):
        return dispatch_add_component(checklist, operation)
    if isinstance(operation, UpdateComponentOperation):
        return dispatch_update_component(checklist, operation)
    if isinstance(operation, DeleteComponentOperation):
        return dispatch_delete_component(checklist, operation)
    if isinstance(operation, MoveComponentOperation):
        return move_component(
            checklist,
            operation.targetId,
            operation.targetContainerId,
            operation.position,
        )

    raise UnsupportedOperationError(f"Unsupported operation payload: {operation}")
