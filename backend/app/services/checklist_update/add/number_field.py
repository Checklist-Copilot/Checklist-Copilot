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
    {"type", "label", "humanReadableId", "value", "unit", "min", "max", "required"}
)


def _validate_optional_number(payload: dict, field: str) -> int | float | None:
    val = payload.get(field)
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise InvalidComponentPayloadError(
            f"numberField: '{field}' must be a number or null"
        )
    return val


def add_number_field(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    DONE (implemented):
    - Generate id for incoming component
    - Validate numberField payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    payload = payload_to_dict(operation.component)

    if payload.get("type") != "numberField":
        raise InvalidComponentPayloadError(
            f"numberField: expected type 'numberField', got {payload.get('type')!r}"
        )

    reject_unknown_fields(payload, _ALLOWED_FIELDS, "numberField")
    label = require_str(payload, "label", "numberField")

    value = _validate_optional_number(payload, "value")
    minimum = _validate_optional_number(payload, "min")
    maximum = _validate_optional_number(payload, "max")

    if minimum is not None and maximum is not None and minimum > maximum:
        raise InvalidComponentPayloadError(
            "numberField: 'min' must be less than or equal to 'max'"
        )

    unit = payload.get("unit")
    if unit is not None and not isinstance(unit, str):
        raise InvalidComponentPayloadError(
            "numberField: 'unit' must be a string or null"
        )

    component: dict = {
        "id": generate_component_id("numberField"),
        "type": "numberField",
        "label": label,
        "value": value,
        "unit": unit,
        "min": minimum,
        "max": maximum,
        "required": bool(payload.get("required", False)),
        # `edited` is server-controlled. New components are unedited.
        "edited": False,
    }
    if payload.get("humanReadableId") is not None:
        component["humanReadableId"] = payload["humanReadableId"]

    return insert_into_container(
        checklist, operation.targetContainerId, component, operation.position
    )
