from app.schemas.checklist_operations import AddComponentOperation


def add_number_field(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    TODO:
    - Generate id for incoming component
    - Validate numberField payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    raise NotImplementedError("add_number_field is not implemented yet")
