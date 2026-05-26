from app.schemas.checklist_operations import AddComponentOperation
from app.services.checklist_update._common import (
    payload_to_dict,
    reject_unknown_fields,
    require_str,
)
from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.ids import generate_component_id
from app.services.checklist_update.tree_utils import insert_into_container


_ALLOWED_FIELDS = frozenset(
    {
        "type",
        "label",
        "humanReadableId",
        "value",
        "placeholder",
        "required",
        "multiline",
    }
)


def add_text_field(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    DONE (implemented):
    - Generate id for incoming component
    - Validate textField payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    payload = payload_to_dict(operation.component)

    if payload.get("type") != "textField":
        raise InvalidComponentPayloadError(
            f"textField: expected type 'textField', got {payload.get('type')!r}"
        )

    reject_unknown_fields(payload, _ALLOWED_FIELDS, "textField")
    label = require_str(payload, "label", "textField")

    value = payload.get("value", "")
    if not isinstance(value, str):
        raise InvalidComponentPayloadError("textField: 'value' must be a string")

    placeholder = payload.get("placeholder")
    if placeholder is not None and not isinstance(placeholder, str):
        raise InvalidComponentPayloadError(
            "textField: 'placeholder' must be a string or null"
        )

    component: dict = {
        "id": generate_component_id("textField"),
        "type": "textField",
        "label": label,
        "value": value,
        "placeholder": placeholder,
        "required": bool(payload.get("required", False)),
        "multiline": bool(payload.get("multiline", False)),
    }
    if payload.get("humanReadableId") is not None:
        component["humanReadableId"] = payload["humanReadableId"]

    return insert_into_container(
        checklist, operation.targetContainerId, component, operation.position
    )
