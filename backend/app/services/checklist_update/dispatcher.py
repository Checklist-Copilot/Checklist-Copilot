from app.schemas.checklist_operations import AddComponentOperation, ChecklistOperation, DeleteComponentOperation, UpdateComponentOperation
from app.services.checklist_update.add.dispatcher import dispatch_add_component
from app.services.checklist_update.delete.dispatcher import dispatch_delete_component
from app.services.checklist_update.exceptions import UnsupportedOperationError
from app.services.checklist_update.update.dispatcher import dispatch_update_component


def dispatch_operation(checklist: dict, operation: ChecklistOperation) -> dict:
    if isinstance(operation, AddComponentOperation):
        return dispatch_add_component(checklist, operation)
    if isinstance(operation, UpdateComponentOperation):
        return dispatch_update_component(checklist, operation)
    if isinstance(operation, DeleteComponentOperation):
        return dispatch_delete_component(checklist, operation)

    raise UnsupportedOperationError(f"Unsupported operation payload: {operation}")
