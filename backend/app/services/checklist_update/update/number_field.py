from app.schemas.checklist_operations import UpdateComponentOperation


def update_number_field(checklist: dict, operation: UpdateComponentOperation) -> dict:
    """
    TODO:
    - Validate patch fields allowed for numberField
    - Apply component-specific transformations if needed
    """
    raise NotImplementedError("update_number_field is not implemented yet")
