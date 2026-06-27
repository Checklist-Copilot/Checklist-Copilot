import logging
from typing import Any

from app.schemas.checklist_operations import (
    AddComponentOperation,
    ChecklistOperation,
    DeleteComponentOperation,
    DeleteTableColumnOperation,
    DeleteTableRowOperation,
    UpdateComponentOperation,
)
from app.services.checklist_update.add.dispatcher import dispatch_add_component
from app.services.checklist_update.delete.dispatcher import dispatch_delete_component
from app.services.checklist_update.exceptions import UnsupportedOperationError
from app.services.checklist_update.tree_utils import delete_table_column_by_id, delete_table_row_by_id
from app.services.checklist_update.update.dispatcher import dispatch_update_component

logger = logging.getLogger(__name__)


def _operation_log_context(operation: ChecklistOperation) -> dict[str, Any]:
    """Build a compact log payload for checklist operations without dumping the whole checklist tree."""
    if isinstance(operation, AddComponentOperation):
        component = operation.component if isinstance(operation.component, dict) else operation.component.model_dump()
        return {
            "operation": operation.operation,
            "targetContainerId": operation.targetContainerId,
            "componentType": component.get("type"),
            "componentLabel": component.get("label"),
            "humanReadableId": component.get("humanReadableId"),
        }
    if isinstance(operation, UpdateComponentOperation):
        return {
            "operation": operation.operation,
            "targetId": operation.targetId,
            "patchKeys": sorted(operation.patch.keys()),
            "patch": operation.patch,
        }
    if isinstance(operation, DeleteComponentOperation):
        return {"operation": operation.operation, "targetId": operation.targetId}
    if isinstance(operation, DeleteTableColumnOperation):
        return {"operation": operation.operation, "targetId": operation.targetId, "columnId": operation.columnId}
    if isinstance(operation, DeleteTableRowOperation):
        return {"operation": operation.operation, "targetId": operation.targetId, "rowId": operation.rowId}

    return {"operation": type(operation).__name__, "payload": repr(operation)}


def dispatch_operation(checklist: dict, operation: ChecklistOperation) -> dict:
    """Apply one checklist operation and log whether the handler succeeded or rejected it."""
    log_context = _operation_log_context(operation)
    logger.info("Checklist operation start: %s", log_context)

    try:
        if isinstance(operation, AddComponentOperation):
            updated = dispatch_add_component(checklist, operation)
        elif isinstance(operation, UpdateComponentOperation):
            updated = dispatch_update_component(checklist, operation)
        elif isinstance(operation, DeleteComponentOperation):
            updated = dispatch_delete_component(checklist, operation)
        elif isinstance(operation, DeleteTableColumnOperation):
            updated = delete_table_column_by_id(checklist, operation.targetId, operation.columnId)
        elif isinstance(operation, DeleteTableRowOperation):
            updated = delete_table_row_by_id(checklist, operation.targetId, operation.rowId)
        else:
            raise UnsupportedOperationError(f"Unsupported operation payload: {operation}")
    except Exception:
        logger.exception("Checklist operation failed: %s", log_context)
        raise

    logger.info("Checklist operation success: %s", log_context)
    return updated
