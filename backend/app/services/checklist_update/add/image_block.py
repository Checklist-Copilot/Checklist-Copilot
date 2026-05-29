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
    {"type", "label", "humanReadableId", "images", "allowUpload"}
)
_REQUIRED_IMAGE_KEYS = {"imageId", "url"}


def _validate_image_entry(entry: object, index: int) -> dict:
    if not isinstance(entry, dict):
        raise InvalidComponentPayloadError(
            f"imageBlock.images[{index}] must be an object"
        )
    missing = _REQUIRED_IMAGE_KEYS - entry.keys()
    if missing:
        raise InvalidComponentPayloadError(
            f"imageBlock.images[{index}] missing required fields: {sorted(missing)}"
        )
    if not isinstance(entry["imageId"], str) or not isinstance(entry["url"], str):
        raise InvalidComponentPayloadError(
            f"imageBlock.images[{index}]: 'imageId' and 'url' must be strings"
        )
    caption = entry.get("caption")
    if caption is not None and not isinstance(caption, str):
        raise InvalidComponentPayloadError(
            f"imageBlock.images[{index}]: 'caption' must be a string or null"
        )
    return {
        "imageId": entry["imageId"],
        "url": entry["url"],
        "caption": caption,
    }


def add_image_block(checklist: dict, operation: AddComponentOperation) -> dict:
    """
    DONE (implemented):
    - Generate id for incoming component
    - Validate imageBlock payload shape
    - Insert under operation.targetContainerId at operation.position
    """
    payload = payload_to_dict(operation.component)

    if payload.get("type") != "imageBlock":
        raise InvalidComponentPayloadError(
            f"imageBlock: expected type 'imageBlock', got {payload.get('type')!r}"
        )

    reject_unknown_fields(payload, _ALLOWED_FIELDS, "imageBlock")
    label = require_str(payload, "label", "imageBlock")

    raw_images = payload.get("images", [])
    if not isinstance(raw_images, list):
        raise InvalidComponentPayloadError("imageBlock: 'images' must be a list")
    images = [_validate_image_entry(entry, i) for i, entry in enumerate(raw_images)]

    component: dict = {
        "id": generate_component_id("imageBlock"),
        "type": "imageBlock",
        "label": label,
        "images": images,
        "allowUpload": bool(payload.get("allowUpload", False)),
        # `edited` is server-controlled. New components are unedited.
        "edited": False,
    }
    if payload.get("humanReadableId") is not None:
        component["humanReadableId"] = payload["humanReadableId"]

    return insert_into_container(
        checklist, operation.targetContainerId, component, operation.position
    )
