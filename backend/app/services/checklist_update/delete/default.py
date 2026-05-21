from app.schemas.checklist_operations import DeleteComponentOperation
from app.services.checklist_update.tree_utils import delete_component_by_id


def delete_component_default(checklist: dict, operation: DeleteComponentOperation) -> dict:
    """
    Generic delete behavior for checklist tree nodes.

    TODO:
    - Add component-specific cleanup behavior, e.g. deleting image references from storage.
    """
    return delete_component_by_id(checklist, operation.targetId)
