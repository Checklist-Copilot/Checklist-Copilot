from app.schemas.checklist_operations import AddComponentOperation
from app.services.checklist_update._common import (
    payload_to_dict,
    reject_unknown_fields,
    require_str,
)
from app.services.checklist_update.exceptions import (
    InvalidComponentPayloadError,
    InvalidTargetContainerError,
)
from app.services.checklist_update.ids import generate_component_id
from app.services.checklist_update.tree_utils import (
    find_component_by_id,
    insert_into_container,
)


_ALLOWED_FIELDS = frozenset(
    {"type", "label", "humanReadableId", "checked", "required"}
)


def add_checkbox_item(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    DONE (implemented):
    - Generate id for incoming component
    - Validate checkbox payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    payload = payload_to_dict(operation.component)

    if payload.get("type") != "checkbox":
        raise InvalidComponentPayloadError(
            f"checkbox: expected type 'checkbox', got {payload.get('type')!r}"
        )

    reject_unknown_fields(payload, _ALLOWED_FIELDS, "checkbox")
    label = require_str(payload, "label", "checkbox")

    # Checkbox items are only valid inside a checkboxGroup.
    target_container = find_component_by_id(checklist, operation.targetContainerId)
    if target_container is None:
        raise InvalidTargetContainerError(
            f"Target container not found: {operation.targetContainerId}"
        )
    if target_container.get("type") != "checkboxGroup":
        raise InvalidTargetContainerError(
            "checkbox items can only be added inside a checkboxGroup"
        )

    component: dict = {
        "id": generate_component_id("checkbox"),
        "type": "checkbox",
        "label": label,
        "checked": bool(payload.get("checked", False)),
        "required": bool(payload.get("required", False)),
        # `edited` is server-controlled; new components are always unedited.
        # Clients cannot send this field (not in _ALLOWED_FIELDS).
        "edited": False,
    }
    if payload.get("humanReadableId") is not None:
        component["humanReadableId"] = payload["humanReadableId"]

    return insert_into_container(
        checklist, operation.targetContainerId, component, operation.position
    )
