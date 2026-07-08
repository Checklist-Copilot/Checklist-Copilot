"""
Shared helpers used by both add and update component handlers.

Keeps each handler small by centralising payload normalisation and
the "reject unknown / forbidden fields" check.
"""
from typing import Any

from app.services.checklist_update.exceptions import InvalidComponentPayloadError
from app.services.checklist_update.ids import generate_component_id


# Fields that may never be supplied by the caller (AI or frontend).
# `id` is generated server-side, `type` is fixed at creation time,
# `edited` is set automatically by `update_component_by_id` whenever a leaf
# is patched — clients cannot lie about it.
FORBIDDEN_PATCH_FIELDS: frozenset[str] = frozenset({"id", "type", "edited"})


def payload_to_dict(component: Any) -> dict[str, Any]:
    """
    Normalise the `component` field of an AddComponentOperation into a plain dict.

    Accepts either a pydantic model (with model_dump) or a raw dict.
    """
    if hasattr(component, "model_dump"):
        return component.model_dump()
    if isinstance(component, dict):
        return component
    raise InvalidComponentPayloadError(
        f"component payload must be a dict or pydantic model, got {type(component).__name__}"
    )


def patch_to_dict(patch: Any) -> dict[str, Any]:
    """Normalise the `patch` field of an UpdateComponentOperation into a plain dict."""
    if hasattr(patch, "model_dump"):
        return patch.model_dump()
    if isinstance(patch, dict):
        return patch
    raise InvalidComponentPayloadError(
        f"patch must be a dict or pydantic model, got {type(patch).__name__}"
    )


def require_str(payload: dict[str, Any], field: str, component_type: str) -> str:
    """Validate that `field` is present in `payload` and is a non-empty string."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InvalidComponentPayloadError(
            f"{component_type}: '{field}' must be a non-empty string"
        )
    return value


def reject_unknown_fields(
    payload: dict[str, Any],
    allowed: frozenset[str],
    component_type: str,
) -> None:
    """Raise InvalidComponentPayloadError if `payload` contains fields outside `allowed`."""
    # `id` is silently ignored on add (server-generated), so we drop it here.
    unknown = set(payload.keys()) - allowed - {"id"}
    if unknown:
        raise InvalidComponentPayloadError(
            f"{component_type}: unknown fields {sorted(unknown)}"
        )


def _optional_bool(payload: dict[str, Any], field: str, default: bool = False) -> bool:
    value = payload.get(field, default)
    if not isinstance(value, bool):
        raise InvalidComponentPayloadError(f"{payload.get('type', 'component')}: '{field}' must be a boolean")
    return value


def _optional_number(payload: dict[str, Any], field: str) -> int | float | None:
    value = payload.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidComponentPayloadError(f"{payload.get('type', 'component')}: '{field}' must be a number or null")
    return value


def materialize_added_component(payload: dict[str, Any], *, parent_type: str | None = None) -> dict[str, Any]:
    """
    Build a persisted component from a nested add payload.

    The top-level add handlers already generate ids for the component directly
    being added. This helper is for nested payloads sent inside `children` or
    `items`. Without this, AI tool calls that include nested components can
    persist raw objects with no id/default fields, making later manual edits
    ambiguous or impossible.
    """
    if not isinstance(payload, dict):
        raise InvalidComponentPayloadError("nested component must be an object")

    component_type = payload.get("type")

    if component_type == "section":
        reject_unknown_fields(payload, frozenset({"type", "label", "humanReadableId", "collapsed", "children"}), "section")
        children = payload.get("children", [])
        if not isinstance(children, list):
            raise InvalidComponentPayloadError("section: 'children' must be a list")
        component: dict[str, Any] = {
            "id": generate_component_id("section"),
            "type": "section",
            "label": require_str(payload, "label", "section"),
            "collapsed": _optional_bool(payload, "collapsed", False),
            "children": [materialize_added_component(child, parent_type="section") for child in children],
        }
    elif component_type == "checkboxGroup":
        reject_unknown_fields(payload, frozenset({"type", "label", "humanReadableId", "items"}), "checkboxGroup")
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise InvalidComponentPayloadError("checkboxGroup: 'items' must be a list")
        component = {
            "id": generate_component_id("checkboxGroup"),
            "type": "checkboxGroup",
            "label": require_str(payload, "label", "checkboxGroup"),
            "items": [materialize_added_component(item, parent_type="checkboxGroup") for item in items],
        }
    elif component_type == "checkbox":
        if parent_type != "checkboxGroup":
            raise InvalidComponentPayloadError("checkbox: must be nested inside a checkboxGroup")
        reject_unknown_fields(payload, frozenset({"type", "label", "humanReadableId", "checked", "required"}), "checkbox")
        component = {
            "id": generate_component_id("checkbox"),
            "type": "checkbox",
            "label": require_str(payload, "label", "checkbox"),
            "checked": _optional_bool(payload, "checked", False),
            "required": _optional_bool(payload, "required", False),
            "edited": payload.get("checked") is True,
        }
    elif component_type == "textField":
        reject_unknown_fields(payload, frozenset({"type", "label", "humanReadableId", "value", "placeholder", "required", "multiline"}), "textField")
        value = payload.get("value", "")
        if not isinstance(value, str):
            raise InvalidComponentPayloadError("textField: 'value' must be a string")
        placeholder = payload.get("placeholder")
        if placeholder is not None and not isinstance(placeholder, str):
            raise InvalidComponentPayloadError("textField: 'placeholder' must be a string or null")
        component = {
            "id": generate_component_id("textField"),
            "type": "textField",
            "label": require_str(payload, "label", "textField"),
            "value": value,
            "placeholder": placeholder,
            "required": _optional_bool(payload, "required", False),
            "multiline": _optional_bool(payload, "multiline", False),
            "edited": bool(value.strip()),
        }
    elif component_type == "numberField":
        reject_unknown_fields(payload, frozenset({"type", "label", "humanReadableId", "value", "unit", "min", "max", "required"}), "numberField")
        minimum = _optional_number(payload, "min")
        maximum = _optional_number(payload, "max")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise InvalidComponentPayloadError("numberField: 'min' must be less than or equal to 'max'")
        unit = payload.get("unit")
        if unit is not None and not isinstance(unit, str):
            raise InvalidComponentPayloadError("numberField: 'unit' must be a string or null")
        value = _optional_number(payload, "value")
        component = {
            "id": generate_component_id("numberField"),
            "type": "numberField",
            "label": require_str(payload, "label", "numberField"),
            "value": value,
            "unit": unit,
            "min": minimum,
            "max": maximum,
            "required": _optional_bool(payload, "required", False),
            "edited": value is not None,
        }
    elif component_type == "imageBlock":
        reject_unknown_fields(payload, frozenset({"type", "label", "humanReadableId", "images", "allowUpload"}), "imageBlock")
        images = payload.get("images", [])
        if not isinstance(images, list):
            raise InvalidComponentPayloadError("imageBlock: 'images' must be a list")
        component = {
            "id": generate_component_id("imageBlock"),
            "type": "imageBlock",
            "label": require_str(payload, "label", "imageBlock"),
            "images": images,
            "allowUpload": _optional_bool(payload, "allowUpload", False),
            "edited": len(images) > 0,
        }
    elif component_type == "table":
        raise InvalidComponentPayloadError("table: nested table payloads are not supported; add tables with a separate add_component call")
    else:
        raise InvalidComponentPayloadError(f"Unsupported nested component type: {component_type!r}")

    if payload.get("humanReadableId") is not None:
        component["humanReadableId"] = payload["humanReadableId"]
    return component


def materialize_section_children(children: Any) -> list[dict[str, Any]]:
    if not isinstance(children, list):
        raise InvalidComponentPayloadError("section: 'children' must be a list")
    return [materialize_added_component(child, parent_type="section") for child in children]


def materialize_checkbox_items(items: Any) -> list[dict[str, Any]]:
    """Materialize checkboxGroup items, accepting concise AI checkbox payloads."""
    if not isinstance(items, list):
        raise InvalidComponentPayloadError("checkboxGroup: 'items' must be a list")

    normalized_items = []
    for item in items:
        if isinstance(item, dict) and item.get("type") is None:
            normalized_items.append({**item, "type": "checkbox"})
        else:
            normalized_items.append(item)
    return [materialize_added_component(item, parent_type="checkboxGroup") for item in normalized_items]


def validate_patch_fields(
    patch: dict[str, Any],
    allowed: frozenset[str],
    component_type: str,
) -> None:
    """
    Validate an update patch:
      - no forbidden fields (id, type)
      - every supplied key must be in `allowed`
      - patch must contain at least one field
    """
    if not patch:
        raise InvalidComponentPayloadError(
            f"{component_type}: patch must not be empty"
        )

    forbidden = set(patch.keys()) & FORBIDDEN_PATCH_FIELDS
    if forbidden:
        raise InvalidComponentPayloadError(
            f"{component_type}: cannot patch immutable fields {sorted(forbidden)}"
        )

    unknown = set(patch.keys()) - allowed
    if unknown:
        raise InvalidComponentPayloadError(
            f"{component_type}: patch contains unsupported fields {sorted(unknown)}"
        )
