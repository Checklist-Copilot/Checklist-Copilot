from app.schemas.checklist_operations import UpdateComponentOperation
from app.services.checklist_update._common import (
    patch_to_dict,
    validate_patch_fields,
)
from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.tree_utils import update_component_by_id


_ALLOWED_PATCH_FIELDS = frozenset(
    {"label", "humanReadableId", "checked", "required"}
)


def update_checkbox_item(checklist: dict, operation: UpdateComponentOperation) -> dict:
    """
    DONE (implemented):
    - Validate patch fields allowed for checkbox item
    - Apply component-specific transformations if needed
    """
    patch = patch_to_dict(operation.patch)
    validate_patch_fields(patch, _ALLOWED_PATCH_FIELDS, "checkbox")

    if "label" in patch and (not isinstance(patch["label"], str) or not patch["label"].strip()):
        raise InvalidComponentPayloadError("checkbox: 'label' must be a non-empty string")
    if "checked" in patch and not isinstance(patch["checked"], bool):
        raise InvalidComponentPayloadError("checkbox: 'checked' must be a boolean")
    if "required" in patch and not isinstance(patch["required"], bool):
        raise InvalidComponentPayloadError("checkbox: 'required' must be a boolean")

    return update_component_by_id(checklist, operation.targetId, patch)
