"""
Shared helpers used by both add and update component handlers.

Keeps each handler small by centralising payload normalisation and
the "reject unknown / forbidden fields" check.
"""
from typing import Any

from app.services.checklist_update.exceptions import InvalidComponentPayloadError


# Fields that may never be supplied by the caller (AI or frontend).
# `id` is generated server-side, `type` is fixed at creation time.
FORBIDDEN_PATCH_FIELDS: frozenset[str] = frozenset({"id", "type"})


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
