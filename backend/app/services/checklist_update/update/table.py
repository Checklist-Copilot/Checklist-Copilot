import uuid

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


def _blank_value_for_column(column: dict) -> object:
    return None if column.get("type") == "number" else ""


def _update_table_action(checklist: dict, operation: UpdateComponentOperation, patch: dict) -> dict:
    target = find_component_by_id(checklist, operation.targetId)
    if target is None:
        # Let the shared helper raise the project's standard not-found error.
        return update_component_by_id(checklist, operation.targetId, {})
    if target.get("type") != "table":
        raise InvalidComponentPayloadError("tableAction patches can only target tables")

    columns = target.get("columns")
    rows = target.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        raise InvalidComponentPayloadError("table: expected columns and rows lists")

    action = patch.get("tableAction")

    if action == "newRow":
        row = {
            "id": str(uuid.uuid4()),
            "cells": {
                column["id"]: _blank_value_for_column(column)
                for column in columns
                if isinstance(column, dict) and isinstance(column.get("id"), str)
            },
        }
        return update_component_by_id(checklist, operation.targetId, {"rows": [*rows, row]})

    if action == "deleteRow":
        target_id = patch.get("targetId")
        if not isinstance(target_id, str) or not target_id:
            raise InvalidComponentPayloadError("table deleteRow: 'targetId' must be a row id")
        return update_component_by_id(
            checklist,
            operation.targetId,
            {"rows": [row for row in rows if not (isinstance(row, dict) and row.get("id") == target_id)]},
        )

    if action == "newColumn":
        column_type = patch.get("columnType", "text")
        if column_type not in _ALLOWED_COLUMN_TYPES:
            raise InvalidComponentPayloadError("table newColumn: 'columnType' must be 'text' or 'number'")
        label = patch.get("label")
        if not isinstance(label, str) or not label.strip():
            label = f"Column {len(columns) + 1}"
        column = {"id": str(uuid.uuid4()), "label": label.strip(), "type": column_type}
        if column_type == "number":
            unit = patch.get("unit")
            column["unit"] = unit.strip() if isinstance(unit, str) and unit.strip() else None
        next_rows = []
        for row in rows:
            if isinstance(row, dict):
                next_rows.append({
                    **row,
                    "cells": {
                        **(row.get("cells") if isinstance(row.get("cells"), dict) else {}),
                        column["id"]: _blank_value_for_column(column),
                    },
                })
            else:
                next_rows.append(row)
        return update_component_by_id(checklist, operation.targetId, {"columns": [*columns, column], "rows": next_rows})

    if action == "deleteColumn":
        target_id = patch.get("targetId")
        if not isinstance(target_id, str) or not target_id:
            raise InvalidComponentPayloadError("table deleteColumn: 'targetId' must be a column id")
        next_columns = [
            column for column in columns if not (isinstance(column, dict) and column.get("id") == target_id)
        ]
        next_rows = []
        for row in rows:
            if isinstance(row, dict):
                cells = dict(row.get("cells") if isinstance(row.get("cells"), dict) else {})
                cells.pop(target_id, None)
                next_rows.append({**row, "cells": cells})
            else:
                next_rows.append(row)
        return update_component_by_id(checklist, operation.targetId, {"columns": next_columns, "rows": next_rows})

    if action == "cell":
        row_id = patch.get("rowId")
        column_id = patch.get("columnId")
        if not isinstance(row_id, str) or not isinstance(column_id, str):
            raise InvalidComponentPayloadError("table cell: 'rowId' and 'columnId' must be strings")
        column = next((col for col in columns if isinstance(col, dict) and col.get("id") == column_id), None)
        if column is None:
            raise InvalidComponentPayloadError(f"table cell: unknown column id {column_id}")
        value = _validate_cell_value(patch.get("value"), column.get("type"), column_id, 0)
        next_rows = []
        found_row = False
        for row in rows:
            if isinstance(row, dict) and row.get("id") == row_id:
                found_row = True
                next_rows.append({
                    **row,
                    "cells": {
                        **(row.get("cells") if isinstance(row.get("cells"), dict) else {}),
                        column_id: value,
                    },
                })
            else:
                next_rows.append(row)
        if not found_row:
            raise InvalidComponentPayloadError(f"table cell: unknown row id {row_id}")
        return update_component_by_id(checklist, operation.targetId, {"rows": next_rows})

    raise InvalidComponentPayloadError(
        "tableAction must be one of: newRow, deleteRow, newColumn, deleteColumn, cell"
    )


def update_table(checklist: dict, operation: UpdateComponentOperation) -> dict:
    """
    DONE (implemented):
    - Validate patch fields allowed for table
    - Apply component-specific transformations if needed
    """
    patch = patch_to_dict(operation.patch)
    if "tableAction" in patch:
        return _update_table_action(checklist, operation, patch)

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
