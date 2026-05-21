from app.schemas.checklist_operations import AddComponentOperation


def add_checkbox_group(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    TODO:
    - Generate id for incoming component
    - Validate checkboxGroup payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    raise NotImplementedError("add_checkbox_group is not implemented yet")
