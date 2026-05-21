from app.schemas.checklist_operations import AddComponentOperation


def add_checkbox_item(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    TODO:
    - Generate id for incoming component
    - Validate checkbox payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    raise NotImplementedError("add_checkbox_item is not implemented yet")
