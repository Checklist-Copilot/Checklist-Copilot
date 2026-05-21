from app.schemas.checklist_operations import AddComponentOperation


def add_image_block(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    TODO:
    - Generate id for incoming component
    - Validate imageBlock payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    raise NotImplementedError("add_image_block is not implemented yet")
