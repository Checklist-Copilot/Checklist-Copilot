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
    {"label", "humanReadableId", "columns", "rows"}
)
_ALLOWED_COLUMN_TYPES = frozenset({"text", "number"})


def _validate_column(column: object, index: int) -> dict:
    if not isinstance(column, dict):
        raise InvalidComponentPayloadError(f"table.columns[{index}] must be an object")
    col_id = column.get("id")
    label = column.get("label")
    col_type = column.get("type")
    unit = column.get("unit")
    if not isinstance(col_id, str) or not col_id:
        raise InvalidComponentPayloadError(
            f"table.columns[{index}]: 'id' must be a non-empty string"
        )
    if not isinstance(label, str) or not label:
        raise InvalidComponentPayloadError(
            f"table.columns[{index}]: 'label' must be a non-empty string"
        )
    if col_type not in _ALLOWED_COLUMN_TYPES:
        raise InvalidComponentPayloadError(
            f"table.columns[{index}]: 'type' must be one of {sorted(_ALLOWED_COLUMN_TYPES)}"
        )
    if unit is not None and not isinstance(unit, str):
        raise InvalidComponentPayloadError(
            f"table.columns[{index}]: 'unit' must be a string or null"
        )

    validated = {"id": col_id, "label": label, "type": col_type}
    if col_type == "number":
        validated["unit"] = unit.strip() if isinstance(unit, str) and unit.strip() else None
    return validated


def _validate_cell_value(value: object, col_type: str, col_id: str, row_index: int) -> object:
    if col_type == "text":
        if not isinstance(value, str):
            raise InvalidComponentPayloadError(
                f"table.rows[{row_index}].cells['{col_id}']: expected string"
            )
    elif col_type == "number":
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise InvalidComponentPayloadError(
                f"table.rows[{row_index}].cells['{col_id}']: expected number or null"
            )
    return value


def _validate_row(row: object, index: int, columns: list[dict]) -> dict:
    if not isinstance(row, dict):
        raise InvalidComponentPayloadError(f"table.rows[{index}] must be an object")
    row_id = row.get("id")
    if not isinstance(row_id, str) or not row_id:
        raise InvalidComponentPayloadError(
            f"table.rows[{index}]: 'id' must be a non-empty string"
        )
    cells = row.get("cells", {})
    if not isinstance(cells, dict):
        raise InvalidComponentPayloadError(
            f"table.rows[{index}]: 'cells' must be an object"
        )

    column_lookup = {col["id"]: col["type"] for col in columns}
    unknown_keys = set(cells.keys()) - column_lookup.keys()
    if unknown_keys:
        raise InvalidComponentPayloadError(
            f"table.rows[{index}]: cells reference unknown columns {sorted(unknown_keys)}"
        )

    validated_cells: dict = {}
    for col_id, col_type in column_lookup.items():
        if col_id in cells:
            validated_cells[col_id] = _validate_cell_value(
                cells[col_id], col_type, col_id, index
            )

    return {"id": row_id, "cells": validated_cells}


def update_table(checklist: dict, operation: UpdateComponentOperation) -> dict:
    """
    DONE (implemented):
    - Validate patch fields allowed for table
    - Apply component-specific transformations if needed
    """
    patch = patch_to_dict(operation.patch)
    validate_patch_fields(patch, _ALLOWED_PATCH_FIELDS, "table")

    if "label" in patch and (not isinstance(patch["label"], str) or not patch["label"].strip()):
        raise InvalidComponentPayloadError("table: 'label' must be a non-empty string")

    # Resolve effective column set (either patched or existing) so we can validate rows.
    if "columns" in patch:
        if not isinstance(patch["columns"], list):
            raise InvalidComponentPayloadError("table: 'columns' must be a list")
        columns = [_validate_column(col, i) for i, col in enumerate(patch["columns"])]
        column_ids = [c["id"] for c in columns]
        if len(set(column_ids)) != len(column_ids):
            raise InvalidComponentPayloadError("table: column ids must be unique")
        patch["columns"] = columns
    else:
        existing = find_component_by_id(checklist, operation.targetId) or {}
        columns = existing.get("columns", [])

    if "rows" in patch:
        if not isinstance(patch["rows"], list):
            raise InvalidComponentPayloadError("table: 'rows' must be a list")
        patch["rows"] = [
            _validate_row(row, i, columns) for i, row in enumerate(patch["rows"])
        ]

    return update_component_by_id(checklist, operation.targetId, patch)
