from app.schemas.checklist_operations import DeleteComponentOperation
from app.services.checklist_update.delete.default import delete_component_default


def dispatch_delete_component(checklist: dict, operation: DeleteComponentOperation) -> dict:
    return delete_component_default(checklist, operation)
