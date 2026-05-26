from app.schemas.checklist_operations import UpdateComponentOperation
from app.services.checklist_update._common import (
    patch_to_dict,
    validate_patch_fields,
)
from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.tree_utils import update_component_by_id


_ALLOWED_PATCH_FIELDS = frozenset(
    {
        "label",
        "humanReadableId",
        "value",
        "placeholder",
        "required",
        "multiline",
    }
)


def update_text_field(checklist: dict, operation: UpdateComponentOperation) -> dict:
    """
    DONE (implemented):
    - Validate patch fields allowed for textField
    - Apply component-specific transformations if needed
    """
    patch = patch_to_dict(operation.patch)
    validate_patch_fields(patch, _ALLOWED_PATCH_FIELDS, "textField")

    if "label" in patch and (not isinstance(patch["label"], str) or not patch["label"].strip()):
        raise InvalidComponentPayloadError("textField: 'label' must be a non-empty string")
    if "value" in patch and not isinstance(patch["value"], str):
        raise InvalidComponentPayloadError("textField: 'value' must be a string")
    if "placeholder" in patch and patch["placeholder"] is not None and not isinstance(patch["placeholder"], str):
        raise InvalidComponentPayloadError(
            "textField: 'placeholder' must be a string or null"
        )
    if "required" in patch and not isinstance(patch["required"], bool):
        raise InvalidComponentPayloadError("textField: 'required' must be a boolean")
    if "multiline" in patch and not isinstance(patch["multiline"], bool):
        raise InvalidComponentPayloadError("textField: 'multiline' must be a boolean")

    return update_component_by_id(checklist, operation.targetId, patch)
