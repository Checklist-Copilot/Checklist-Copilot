from app.schemas.checklist_operations import UpdateComponentOperation
from app.services.checklist_update._common import (
    patch_to_dict,
    validate_patch_fields,
)
from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.tree_utils import update_component_by_id


# `items` is structural; use addComponent/deleteComponent to add or remove checkboxes.
_ALLOWED_PATCH_FIELDS = frozenset({"label", "humanReadableId"})


def update_checkbox_group(checklist: dict, operation: UpdateComponentOperation) -> dict:
    """
    DONE (implemented):
    - Validate patch fields allowed for checkboxGroup
    - Apply component-specific transformations if needed
    """
    patch = patch_to_dict(operation.patch)
    validate_patch_fields(patch, _ALLOWED_PATCH_FIELDS, "checkboxGroup")

    if "label" in patch and (not isinstance(patch["label"], str) or not patch["label"].strip()):
        raise InvalidComponentPayloadError(
            "checkboxGroup: 'label' must be a non-empty string"
        )

    return update_component_by_id(checklist, operation.targetId, patch)
