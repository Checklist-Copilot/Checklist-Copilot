from app.schemas.checklist_operations import AddComponentOperation
from app.services.checklist_update._common import (
    payload_to_dict,
    reject_unknown_fields,
    require_str,
)
from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.ids import generate_component_id
from app.services.checklist_update.tree_utils import insert_into_container


_ALLOWED_FIELDS = frozenset({"type", "label", "humanReadableId", "collapsed", "children"})


def add_section(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    DONE (implemented):
    - Generate id for incoming component
    - Validate section payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    payload = payload_to_dict(operation.component)

    if payload.get("type") != "section":
        raise InvalidComponentPayloadError(
            f"section: expected type 'section', got {payload.get('type')!r}"
        )

    reject_unknown_fields(payload, _ALLOWED_FIELDS, "section")
    label = require_str(payload, "label", "section")

    children = payload.get("children", [])
    if not isinstance(children, list):
        raise InvalidComponentPayloadError("section: 'children' must be a list")

    component: dict = {
        "id": generate_component_id("section"),
        "type": "section",
        "label": label,
        "collapsed": bool(payload.get("collapsed", False)),
        "children": children,
    }
    if payload.get("humanReadableId") is not None:
        component["humanReadableId"] = payload["humanReadableId"]

    return insert_into_container(
        checklist, operation.targetContainerId, component, operation.position
    )
