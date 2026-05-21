from app.schemas.checklist_operations import AddComponentOperation


def add_table(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    TODO:
    - Generate id for incoming component
    - Validate table payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    raise NotImplementedError("add_table is not implemented yet")
