from typing import Any

from app.services.checklist_update.exceptions import (
    CannotDeleteRootError,
    ComponentNotFoundError,
    InvalidComponentPayloadError,
    InvalidTargetContainerError,
)


# Component types that carry the server-controlled `edited` flag.
# Containers (section, checkboxGroup) are excluded — they aren't "items."
_LEAF_TYPES_WITH_EDITED: frozenset[str] = frozenset(
    {"checkbox", "textField", "numberField", "imageBlock", "table"}
)


def _has_meaningful_user_input(node: dict[str, Any]) -> bool:
    """
    Decide whether a leaf should count as edited.

    `edited` is not a permanent "was touched once" audit flag. It means the
    item currently contains user-provided data. If the user clears a field back
    to its empty/default state, the flag should go back to false.
    """
    ctype = node.get("type")

    if ctype == "checkbox":
        return node.get("checked") is True

    if ctype == "textField":
        value = node.get("value")
        return isinstance(value, str) and value.strip() != ""

    if ctype == "numberField":
        return node.get("value") is not None

    if ctype == "imageBlock":
        images = node.get("images")
        return isinstance(images, list) and len(images) > 0

    if ctype == "table":
        rows = node.get("rows") or []
        if not isinstance(rows, list):
            return False
        for row in rows:
            if not isinstance(row, dict):
                continue
            cells = row.get("cells") or {}
            if not isinstance(cells, dict):
                continue
            for value in cells.values():
                if isinstance(value, str) and value.strip() != "":
                    return True
                if isinstance(value, bool) and value is True:
                    return True
                if value is not None and not isinstance(value, (str, bool)):
                    return True
        return False

    return False


def _iter_child_containers(node: dict[str, Any]) -> list[list[dict[str, Any]]]:
    containers: list[list[dict[str, Any]]] = []
    children = node.get("children")
    if isinstance(children, list):
        containers.append(children)
    items = node.get("items")
    if isinstance(items, list):
        containers.append(items)
    return containers


def find_component_by_id(checklist: dict[str, Any], target_id: str) -> dict[str, Any] | None:
    if checklist.get("id") == target_id:
        return checklist

    for child_list in _iter_child_containers(checklist):
        for child in child_list:
            if isinstance(child, dict):
                found = find_component_by_id(child, target_id)
                if found is not None:
                    return found

    return None


def find_parent_container(checklist: dict[str, Any], target_id: str) -> dict[str, Any] | None:
    for child_list in _iter_child_containers(checklist):
        for child in child_list:
            if isinstance(child, dict):
                if child.get("id") == target_id:
                    return checklist
                found = find_parent_container(child, target_id)
                if found is not None:
                    return found
    return None


# Locates the mutable sibling list that directly contains a component.
# Reorder operations use this to move an existing child without changing parents.
def find_parent_child_list(
    checklist: dict[str, Any],
    target_id: str,
) -> tuple[dict[str, Any], str, list[dict[str, Any]]] | None:
    for key in ("children", "items"):
        child_list = checklist.get(key)
        if not isinstance(child_list, list):
            continue
        for child in child_list:
            if isinstance(child, dict) and child.get("id") == target_id:
                return checklist, key, child_list
        for child in child_list:
            if isinstance(child, dict):
                found = find_parent_child_list(child, target_id)
                if found is not None:
                    return found
    return None


# Detects ids that belong to table internals instead of checklist components.
# Rows and columns are edited through tableAction patches, not component moves.
def find_table_part_by_id(checklist: dict[str, Any], target_id: str) -> tuple[str, str] | None:
    if checklist.get("type") == "table":
        for row in checklist.get("rows", []) or []:
            if isinstance(row, dict) and row.get("id") == target_id:
                return checklist.get("id", ""), "row"
        for column in checklist.get("columns", []) or []:
            if isinstance(column, dict) and column.get("id") == target_id:
                return checklist.get("id", ""), "column"

    for child_list in _iter_child_containers(checklist):
        for child in child_list:
            if isinstance(child, dict):
                found = find_table_part_by_id(child, target_id)
                if found is not None:
                    return found
    return None


# Ensures a requested reorder id points at a real checklist component, not a
# table row/column, and returns its parent sibling list.
def _require_component_sibling_list(
    checklist: dict[str, Any],
    target_id: str,
    *,
    role: str = "target",
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    location = find_parent_child_list(checklist, target_id)
    if location is not None:
        return location
    if find_table_part_by_id(checklist, target_id) is not None:
        raise InvalidTargetContainerError(
            f"Table rows and columns are not checklist components and cannot be used as a {role}. "
            "Use update_component with a tableAction patch for table edits."
        )
    raise ComponentNotFoundError(f"Component not found: {target_id}")


# Moves a component inside its current sibling list. `after_id=None` means the
# target becomes the first child; otherwise it is inserted after that sibling.
def move_component_after(checklist: dict[str, Any], target_id: str, after_id: str | None) -> dict[str, Any]:
    if checklist.get("id") == target_id:
        raise CannotDeleteRootError("Moving the root checklist document is not allowed.")
    if after_id == target_id:
        raise InvalidTargetContainerError("A component cannot be moved after itself.")

    target_location = _require_component_sibling_list(checklist, target_id, role="move target")

    _parent, _key, siblings = target_location
    if after_id is not None:
        after_location = _require_component_sibling_list(checklist, after_id, role="move anchor")
        if after_location[2] is not siblings:
            raise InvalidTargetContainerError("moveComponent can only reorder components within the same parent container.")

    target_index = next(
        index for index, child in enumerate(siblings) if isinstance(child, dict) and child.get("id") == target_id
    )
    if after_id is None and target_index == 0:
        raise InvalidTargetContainerError("moveComponent would not change the order; the component is already first.")
    if after_id is not None:
        previous_sibling = siblings[target_index - 1] if target_index > 0 else None
        if isinstance(previous_sibling, dict) and previous_sibling.get("id") == after_id:
            raise InvalidTargetContainerError(
                "moveComponent would not change the order; targetId is already immediately after afterId."
            )

    target = siblings.pop(target_index)

    if after_id is None:
        siblings.insert(0, target)
        return checklist

    after_index = next(
        index for index, child in enumerate(siblings) if isinstance(child, dict) and child.get("id") == after_id
    )
    siblings.insert(after_index + 1, target)
    return checklist


# Swaps two existing components in the same sibling list. This is intentionally
# separate from move_component because user requests that say "swap A and B" map
# to a single deterministic operation instead of an error-prone pair of moves.
def swap_components(checklist: dict[str, Any], first_id: str, second_id: str) -> dict[str, Any]:
    if checklist.get("id") in {first_id, second_id}:
        raise CannotDeleteRootError("Moving the root checklist document is not allowed.")
    if first_id == second_id:
        raise InvalidTargetContainerError("swapComponent requires two different component ids.")

    first_location = _require_component_sibling_list(checklist, first_id, role="swap target")
    second_location = _require_component_sibling_list(checklist, second_id, role="swap target")
    if first_location[2] is not second_location[2]:
        raise InvalidTargetContainerError("swapComponent can only swap components within the same parent container.")

    siblings = first_location[2]
    first_index = next(
        index for index, child in enumerate(siblings) if isinstance(child, dict) and child.get("id") == first_id
    )
    second_index = next(
        index for index, child in enumerate(siblings) if isinstance(child, dict) and child.get("id") == second_id
    )
    siblings[first_index], siblings[second_index] = siblings[second_index], siblings[first_index]
    return checklist


def insert_into_container(
    checklist: dict[str, Any],
    target_container_id: str,
    component: dict[str, Any],
    position: str | dict[str, Any],
) -> dict[str, Any]:
    container = find_component_by_id(checklist, target_container_id)
    if container is None:
        raise InvalidTargetContainerError(f"Target container not found: {target_container_id}")

    # For now we support section.children and checkboxGroup.items only.
    target_list = container.get("children")
    if not isinstance(target_list, list):
        target_list = container.get("items")

    if not isinstance(target_list, list):
        raise InvalidTargetContainerError(
            f"Component {target_container_id} is not a supported container (expected children/items list)."
        )

    if isinstance(position, str):
        if position == "start":
            target_list.insert(0, component)
        else:
            # Default to end for skeleton.
            target_list.append(component)
        return checklist

    # TODO: support index-based or relative positioning strategies.
    target_list.append(component)
    return checklist


def delete_component_by_id(checklist: dict[str, Any], target_id: str) -> dict[str, Any]:
    if checklist.get("id") == target_id:
        raise CannotDeleteRootError("Deleting the root checklist document is not allowed.")

    parent = find_parent_container(checklist, target_id)
    if parent is None:
        raise ComponentNotFoundError(f"Component not found: {target_id}")

    for key in ("children", "items"):
        container = parent.get(key)
        if isinstance(container, list):
            parent[key] = [item for item in container if not (isinstance(item, dict) and item.get("id") == target_id)]

    return checklist


def delete_table_column_by_id(checklist: dict[str, Any], target_id: str, column_id: str) -> dict[str, Any]:
    """Remove one column from a table and strip the matching cell from every row."""
    target = find_component_by_id(checklist, target_id)
    if target is None:
        raise ComponentNotFoundError(f"Component not found: {target_id}")
    if target.get("type") != "table":
        raise InvalidComponentPayloadError(f"Component is not a table: {target_id}")

    columns = target.get("columns")
    rows = target.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        raise InvalidComponentPayloadError("table: expected columns and rows lists")
    if not any(isinstance(column, dict) and column.get("id") == column_id for column in columns):
        raise ComponentNotFoundError(f"Table column not found: {column_id}")

    target["columns"] = [
        column for column in columns if not (isinstance(column, dict) and column.get("id") == column_id)
    ]
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("cells"), dict):
            row["cells"].pop(column_id, None)

    target["edited"] = _has_meaningful_user_input(target)
    return checklist


def delete_table_row_by_id(checklist: dict[str, Any], target_id: str, row_id: str) -> dict[str, Any]:
    """Remove one row from a table without changing the table's columns."""
    target = find_component_by_id(checklist, target_id)
    if target is None:
        raise ComponentNotFoundError(f"Component not found: {target_id}")
    if target.get("type") != "table":
        raise InvalidComponentPayloadError(f"Component is not a table: {target_id}")

    rows = target.get("rows")
    if not isinstance(rows, list):
        raise InvalidComponentPayloadError("table: expected rows list")
    if not any(isinstance(row, dict) and row.get("id") == row_id for row in rows):
        raise ComponentNotFoundError(f"Table row not found: {row_id}")

    target["rows"] = [row for row in rows if not (isinstance(row, dict) and row.get("id") == row_id)]
    target["edited"] = _has_meaningful_user_input(target)
    return checklist


def update_component_by_id(checklist: dict[str, Any], target_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    target = find_component_by_id(checklist, target_id)
    if target is None:
        raise ComponentNotFoundError(f"Component not found: {target_id}")

    target.update(patch)

    # Server-controlled edited flag. The patch itself can never contain
    # `edited` (rejected upstream in validate_patch_fields), so this is the
    # only place it changes. It reflects whether the component currently has
    # meaningful user input, not merely whether it was touched in the past.
    if target.get("type") in _LEAF_TYPES_WITH_EDITED:
        target["edited"] = _has_meaningful_user_input(target)

    return checklist
