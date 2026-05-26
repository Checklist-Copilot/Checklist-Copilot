from app.schemas.checklist_operations import UpdateComponentOperation
from app.services.checklist_update._common import (
    patch_to_dict,
    validate_patch_fields,
)
from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.tree_utils import update_component_by_id


# Structural fields (children) cannot be patched directly;
# use add/delete operations to mutate the tree instead.
_ALLOWED_PATCH_FIELDS = frozenset({"label", "humanReadableId", "collapsed"})


def update_section(checklist: dict, operation: UpdateComponentOperation) -> dict:
    """
    DONE (implemented):
    - Validate patch fields allowed for section
    - Apply component-specific transformations if needed
    """
    patch = patch_to_dict(operation.patch)
    validate_patch_fields(patch, _ALLOWED_PATCH_FIELDS, "section")

    if "label" in patch and (not isinstance(patch["label"], str) or not patch["label"].strip()):
        raise InvalidComponentPayloadError("section: 'label' must be a non-empty string")
    if "collapsed" in patch and not isinstance(patch["collapsed"], bool):
        raise InvalidComponentPayloadError("section: 'collapsed' must be a boolean")

    return update_component_by_id(checklist, operation.targetId, patch)
