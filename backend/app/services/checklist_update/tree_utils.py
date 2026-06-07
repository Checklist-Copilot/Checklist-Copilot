from typing import Any

from app.services.checklist_update.exceptions import CannotDeleteRootError, ComponentNotFoundError, InvalidTargetContainerError


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
