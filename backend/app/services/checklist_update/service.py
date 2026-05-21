from app.schemas.checklist_operations import ChecklistOperation
from app.services.checklist_update.dispatcher import dispatch_operation


def apply_checklist_operations(checklist: dict, operations: list[ChecklistOperation]) -> dict:
    """
    Entry point shared by both manual frontend edits and AI-generated tool calls.

    Example payload:
    {
      "operations": [
        {"operation": "addComponent", ...},
        {"operation": "updateComponent", ...},
        {"operation": "deleteComponent", ...}
      ]
    }
    """
    for operation in operations:
        checklist = dispatch_operation(checklist, operation)
    return checklist
