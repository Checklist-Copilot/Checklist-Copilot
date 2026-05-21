from app.schemas.checklist_operations import AddComponentOperation


def add_section(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    TODO:
    - Generate id for incoming component
    - Validate section payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    raise NotImplementedError("add_section is not implemented yet")
