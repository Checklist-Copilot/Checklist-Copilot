from app.schemas.checklist_operations import UpdateComponentOperation
from app.services.checklist_update._common import (
    patch_to_dict,
    validate_patch_fields,
)
from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.tree_utils import (
    find_component_by_id,
    update_component_by_id,
)


_ALLOWED_PATCH_FIELDS = frozenset(
    {"label", "humanReadableId", "value", "unit", "min", "max", "required"}
)


def _is_number_or_none(val: object) -> bool:
    if val is None:
        return True
    if isinstance(val, bool):
        return False
    return isinstance(val, (int, float))


def update_number_field(checklist: dict, operation: UpdateComponentOperation) -> dict:
    """
    DONE (implemented):
    - Validate patch fields allowed for numberField
    - Apply component-specific transformations if needed
    """
    patch = patch_to_dict(operation.patch)
    validate_patch_fields(patch, _ALLOWED_PATCH_FIELDS, "numberField")

    if "label" in patch and (not isinstance(patch["label"], str) or not patch["label"].strip()):
        raise InvalidComponentPayloadError("numberField: 'label' must be a non-empty string")
    for field in ("value", "min", "max"):
        if field in patch and not _is_number_or_none(patch[field]):
            raise InvalidComponentPayloadError(
                f"numberField: '{field}' must be a number or null"
            )
    if "unit" in patch and patch["unit"] is not None and not isinstance(patch["unit"], str):
        raise InvalidComponentPayloadError("numberField: 'unit' must be a string or null")
    if "required" in patch and not isinstance(patch["required"], bool):
        raise InvalidComponentPayloadError("numberField: 'required' must be a boolean")

    # Cross-field validation: combine patched + existing min/max to ensure min <= max.
    if "min" in patch or "max" in patch:
        existing = find_component_by_id(checklist, operation.targetId) or {}
        minimum = patch["min"] if "min" in patch else existing.get("min")
        maximum = patch["max"] if "max" in patch else existing.get("max")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise InvalidComponentPayloadError(
                "numberField: 'min' must be less than or equal to 'max'"
            )

    return update_component_by_id(checklist, operation.targetId, patch)
