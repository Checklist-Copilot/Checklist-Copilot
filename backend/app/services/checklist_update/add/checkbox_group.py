from app.schemas.checklist_operations import AddComponentOperation
from app.services.checklist_update._common import (
    payload_to_dict,
    reject_unknown_fields,
    require_str,
)
from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.ids import generate_component_id
from app.services.checklist_update.tree_utils import insert_into_container


_ALLOWED_FIELDS = frozenset({"type", "label", "humanReadableId", "items"})


def add_checkbox_group(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    DONE (implemented):
    - Generate id for incoming component
    - Validate checkboxGroup payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    payload = payload_to_dict(operation.component)

    if payload.get("type") != "checkboxGroup":
        raise InvalidComponentPayloadError(
            f"checkboxGroup: expected type 'checkboxGroup', got {payload.get('type')!r}"
        )

    reject_unknown_fields(payload, _ALLOWED_FIELDS, "checkboxGroup")
    label = require_str(payload, "label", "checkboxGroup")

    items = payload.get("items", [])
    if not isinstance(items, list):
        raise InvalidComponentPayloadError("checkboxGroup: 'items' must be a list")

    component: dict = {
        "id": generate_component_id("checkboxGroup"),
        "type": "checkboxGroup",
        "label": label,
        "items": items,
    }
    if payload.get("humanReadableId") is not None:
        component["humanReadableId"] = payload["humanReadableId"]

    return insert_into_container(
        checklist, operation.targetContainerId, component, operation.position
    )
