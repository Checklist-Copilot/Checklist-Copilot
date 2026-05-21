from app.schemas.checklist_operations import AddComponentOperation


def add_text_field(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    TODO:
    - Generate id for incoming component
    - Validate textField payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    raise NotImplementedError("add_text_field is not implemented yet")
