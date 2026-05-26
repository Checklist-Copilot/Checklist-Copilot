from app.schemas.checklist_operations import UpdateComponentOperation
from app.services.checklist_update._common import (
    patch_to_dict,
    validate_patch_fields,
)
from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.tree_utils import update_component_by_id


_ALLOWED_PATCH_FIELDS = frozenset(
    {"label", "humanReadableId", "images", "allowUpload"}
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
    return {"imageId": entry["imageId"], "url": entry["url"], "caption": caption}


def update_image_block(checklist: dict, operation: UpdateComponentOperation) -> dict:
    """
    DONE (implemented):
    - Validate patch fields allowed for imageBlock
    - Apply component-specific transformations if needed
    """
    patch = patch_to_dict(operation.patch)
    validate_patch_fields(patch, _ALLOWED_PATCH_FIELDS, "imageBlock")

    if "label" in patch and (not isinstance(patch["label"], str) or not patch["label"].strip()):
        raise InvalidComponentPayloadError("imageBlock: 'label' must be a non-empty string")
    if "allowUpload" in patch and not isinstance(patch["allowUpload"], bool):
        raise InvalidComponentPayloadError("imageBlock: 'allowUpload' must be a boolean")

    if "images" in patch:
        raw_images = patch["images"]
        if not isinstance(raw_images, list):
            raise InvalidComponentPayloadError("imageBlock: 'images' must be a list")
        patch["images"] = [
            _validate_image_entry(entry, i) for i, entry in enumerate(raw_images)
        ]

    return update_component_by_id(checklist, operation.targetId, patch)
