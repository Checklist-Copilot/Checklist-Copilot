"""
Cheap completion stats for a checklist JSON tree.

`recount(checklist_json)` walks the tree once and returns
`{"total": int, "edited": int, "completed": int}`. The caller stores these as
denormalized columns on the `checklists` row so the dashboard can show progress
without loading the heavy JSON for every row.

Definitions (agreed with the team):

- "item"           = any leaf component (checkbox, textField, numberField,
                     imageBlock, table). Sections and checkboxGroups are
                     containers and do not count.
- "edited"         = the item's `edited` flag is true. Server-controlled,
                     set by `tree_utils.update_component_by_id`.
- "completed"      = the item meets its type-specific done criterion:
    checkbox     -> checked === true
    textField    -> value is a non-empty string
    numberField  -> value is not null
    imageBlock   -> images list is non-empty
    table        -> every required cell in every row is filled
                    (required = column.required === true; if no required
                    columns, the table counts as completed when it has at
                    least one row)
"""
from __future__ import annotations

from typing import Any


_LEAF_TYPES: frozenset[str] = frozenset(
    {"checkbox", "textField", "numberField", "imageBlock", "table"}
)


# --------------------------------------------------------------------------- #
# Per-type completion checks                                                   #
# --------------------------------------------------------------------------- #

def _is_completed_checkbox(node: dict[str, Any]) -> bool:
    return node.get("checked") is True


def _is_completed_text_field(node: dict[str, Any]) -> bool:
    value = node.get("value")
    return isinstance(value, str) and value.strip() != ""


def _is_completed_number_field(node: dict[str, Any]) -> bool:
    return node.get("value") is not None


def _is_completed_image_block(node: dict[str, Any]) -> bool:
    images = node.get("images")
    return isinstance(images, list) and len(images) > 0


def _is_completed_table(node: dict[str, Any]) -> bool:
    """
    Table is completed when every required cell is filled. If the table has
    no `required` columns at all, fall back to "has at least one row."
    """
    columns = node.get("columns") or []
    rows = node.get("rows") or []
    if not isinstance(columns, list) or not isinstance(rows, list):
        return False

    required_cols = [c for c in columns if isinstance(c, dict) and c.get("required") is True]
    if not required_cols:
        return len(rows) > 0

    if not rows:
        return False

    for row in rows:
        if not isinstance(row, dict):
            return False
        cells = row.get("cells") or {}
        for col in required_cols:
            value = cells.get(col["id"])
            if not _cell_is_filled(value, col.get("type")):
                return False
    return True


def _cell_is_filled(value: Any, col_type: str | None) -> bool:
    if col_type == "text":
        return isinstance(value, str) and value.strip() != ""
    if col_type == "number":
        return value is not None and not isinstance(value, bool)
    if col_type == "checkbox":
        return value is True
    return value is not None


_COMPLETION_BY_TYPE = {
    "checkbox": _is_completed_checkbox,
    "textField": _is_completed_text_field,
    "numberField": _is_completed_number_field,
    "imageBlock": _is_completed_image_block,
    "table": _is_completed_table,
}


# --------------------------------------------------------------------------- #
# Tree walk                                                                    #
# --------------------------------------------------------------------------- #

def _walk(node: Any, counts: dict[str, int]) -> None:
    if not isinstance(node, dict):
        return

    ctype = node.get("type")
    if ctype in _LEAF_TYPES:
        counts["total"] += 1
        if node.get("edited") is True:
            counts["edited"] += 1
        check = _COMPLETION_BY_TYPE.get(ctype)
        if check is not None and check(node):
            counts["completed"] += 1
        # Leaves don't have children to recurse into.
        return

    # Containers: section.children, checkboxGroup.items, root.children
    for key in ("children", "items"):
        sub = node.get(key)
        if isinstance(sub, list):
            for child in sub:
                _walk(child, counts)


def recount(checklist: dict[str, Any]) -> dict[str, int]:
    """
    Walk the checklist tree and return {total, edited, completed}.
    Cheap — single pass, O(number of components).
    """
    counts = {"total": 0, "edited": 0, "completed": 0}
    _walk(checklist, counts)
    return counts
