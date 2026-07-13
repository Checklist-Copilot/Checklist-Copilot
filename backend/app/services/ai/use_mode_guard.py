"""Deterministic permission guard for AI tool calls in checklist use mode."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.services.ai.openai_client import ToolCall
from app.services.checklist_update.tree_utils import find_component_by_id

AiChecklistMode = Literal["edit", "use"]


@dataclass(frozen=True)
class UseModeGuardResult:
    """Represents whether a proposed AI tool call may execute in use mode."""
    allowed: bool
    reason: str | None = None


_ALLOWED_VALUE_PATCHES_BY_TYPE = {
    "checkbox": {"checked"},
    "textField": {"value"},
    "numberField": {"value"},
}


# Validates an AI tool call against the stricter use-mode permission boundary.
# Use mode may only change existing values, table cells, and image attachments.
def validate_use_mode_tool_call(checklist: dict[str, Any], call: ToolCall) -> UseModeGuardResult:
    if call.name == "add_image_to_block":
        return _validate_add_image_to_block(checklist, call.arguments)

    if call.name == "add_component":
        return UseModeGuardResult(False, "This checklist is in use mode, so I cannot add new checklist components. Use mode only allows filling existing values and managing images.")

    if call.name == "delete_component":
        return UseModeGuardResult(False, "This checklist is in use mode, so I cannot delete checklist components. Use mode only allows filling existing values and managing images.")

    if call.name in {"move_component", "swap_component"}:
        return UseModeGuardResult(False, "This checklist is in use mode, so I cannot reorder checklist components. Use mode only allows filling existing values and managing images.")

    if call.name != "update_component":
        return UseModeGuardResult(False, f"Use mode does not allow tool {call.name!r}.")

    return _validate_update_component(checklist, call.arguments)


# Ensures the vision helper only attaches images to existing image blocks.
def _validate_add_image_to_block(checklist: dict[str, Any], args: dict[str, Any]) -> UseModeGuardResult:
    target_id = args.get("targetBlockId")
    target = find_component_by_id(checklist, target_id) if isinstance(target_id, str) else None
    if target is None:
        return UseModeGuardResult(False, "This checklist is in use mode, so I can only attach images to an existing image block.")
    if target.get("type") != "imageBlock":
        return UseModeGuardResult(False, "This checklist is in use mode, so I can only attach images to imageBlock components.")
    return UseModeGuardResult(True)


# Allows only value-like patches: leaf values, table cell values, and image arrays.
def _validate_update_component(checklist: dict[str, Any], args: dict[str, Any]) -> UseModeGuardResult:
    target_id = args.get("targetId")
    patch = args.get("patch")
    if not isinstance(target_id, str) or not isinstance(patch, dict):
        return UseModeGuardResult(False, "This checklist is in use mode, so update calls must target an existing value with a patch object.")

    target = find_component_by_id(checklist, target_id)
    if target is None:
        return UseModeGuardResult(False, "This checklist is in use mode, so I can only update existing checklist components.")

    component_type = target.get("type")
    if component_type == "table":
        return _validate_table_update(patch)

    if component_type == "imageBlock":
        return _validate_image_block_update(target, patch)

    allowed_keys = _ALLOWED_VALUE_PATCHES_BY_TYPE.get(component_type)
    if allowed_keys is None:
        return UseModeGuardResult(False, f"This checklist is in use mode, so I cannot update {component_type!r} components because they have no user value.")

    patch_keys = set(patch.keys())
    if patch_keys and patch_keys <= allowed_keys:
        return UseModeGuardResult(True)

    return UseModeGuardResult(
        False,
        "This checklist is in use mode, so I can only update component values. I cannot rename labels, change settings, or restructure components.",
    )


# Allows removing existing image references. Adding images is handled by add_image_to_block,
# which injects the uploaded file id/url from the trusted request context.
def _validate_image_block_update(target: dict[str, Any], patch: dict[str, Any]) -> UseModeGuardResult:
    patch_keys = set(patch.keys())
    if not patch_keys or patch_keys != {"images"}:
        return UseModeGuardResult(False, "This checklist is in use mode, so I can only add or remove imageBlock images, not change imageBlock settings.")

    next_images = patch.get("images")
    if not isinstance(next_images, list):
        return UseModeGuardResult(False, "This checklist is in use mode, so image updates must provide an images array.")

    existing_ids = {
        image.get("imageId")
        for image in target.get("images", []) or []
        if isinstance(image, dict) and isinstance(image.get("imageId"), str)
    }
    next_ids = {
        image.get("imageId")
        for image in next_images
        if isinstance(image, dict) and isinstance(image.get("imageId"), str)
    }
    if next_ids <= existing_ids:
        return UseModeGuardResult(True)

    return UseModeGuardResult(
        False,
        "This checklist is in use mode, so I can add images only through add_image_to_block with an uploaded image; update_component may only remove existing image references.",
    )


# Restricts table edits in use mode to existing cell values, never rows or columns.
def _validate_table_update(patch: dict[str, Any]) -> UseModeGuardResult:
    action = patch.get("tableAction")
    if action == "cell":
        if all(isinstance(patch.get(key), str) for key in ("rowId", "columnId")) and "value" in patch:
            return UseModeGuardResult(True)
        return UseModeGuardResult(False, "This checklist is in use mode, so table cell updates require rowId, columnId, and value.")

    if action in {"newRow", "deleteRow", "newColumn", "deleteColumn"}:
        return UseModeGuardResult(False, "This checklist is in use mode, so I cannot add or remove table rows or columns. Use mode only allows updating existing table cell values.")

    return UseModeGuardResult(False, "This checklist is in use mode, so I can only update existing table cell values with tableAction='cell'.")
