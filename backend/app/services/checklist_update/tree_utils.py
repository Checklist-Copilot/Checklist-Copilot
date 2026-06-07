from typing import Any

from app.services.checklist_update.exceptions import CannotDeleteRootError, ComponentNotFoundError, InvalidTargetContainerError


# Component types that carry the server-controlled `edited` flag.
# Containers (section, checkboxGroup) are excluded — they aren't "items."
_LEAF_TYPES_WITH_EDITED: frozenset[str] = frozenset(
    {"checkbox", "textField", "numberField", "imageBlock", "table"}
)


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


def move_component(
    checklist: dict[str, Any],
    target_id: str,
    target_container_id: str,
    position: int,
) -> dict[str, Any]:
    """
    Reorder/relocate a component to a new container at a new index.

    Mechanics:
      1. Find the target's current parent and remove it from that parent's
         children/items list (whichever it lives in).
      2. Find the destination container by id and pick the right list
         (`children` for sections + root, `items` for checkboxGroup).
      3. Insert at `position` (clamped to [0, len]).

    Raises:
      ComponentNotFoundError      — target id doesn't exist in the tree.
      InvalidTargetContainerError — destination container doesn't exist or
                                    can't hold the moved component.
      CannotDeleteRootError       — caller tried to move the root itself.
    """
    if checklist.get("id") == target_id:
        raise CannotDeleteRootError("Cannot move the root checklist document.")

    # 1. Locate the target and detach it from its current parent.
    target_node: dict[str, Any] | None = None
    current_parent = find_parent_container(checklist, target_id)
    if current_parent is None:
        raise ComponentNotFoundError(f"Component not found: {target_id}")

    for key in ("children", "items"):
        container = current_parent.get(key)
        if isinstance(container, list):
            for i, item in enumerate(container):
                if isinstance(item, dict) and item.get("id") == target_id:
                    target_node = container.pop(i)
                    break
            if target_node is not None:
                break
    if target_node is None:
        raise ComponentNotFoundError(f"Component not found: {target_id}")

    # 2. Locate destination container and the right list inside it.
    destination = find_component_by_id(checklist, target_container_id)
    if destination is None:
        raise InvalidTargetContainerError(
            f"Target container not found: {target_container_id}"
        )
    dest_list: list[dict[str, Any]] | None
    target_type = target_node.get("type")
    if target_type == "checkbox":
        dest_list = destination.get("items") if isinstance(destination.get("items"), list) else None
    else:
        dest_list = destination.get("children") if isinstance(destination.get("children"), list) else None
    if dest_list is None:
        raise InvalidTargetContainerError(
            f"Component {target_container_id} cannot hold a {target_type!r} (no matching children/items list)."
        )

    # 3. Insert at the clamped position.
    if position < 0:
        position = max(0, len(dest_list) + position)
    position = min(position, len(dest_list))
    dest_list.insert(position, target_node)
    return checklist


def update_component_by_id(checklist: dict[str, Any], target_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    target = find_component_by_id(checklist, target_id)
    if target is None:
        raise ComponentNotFoundError(f"Component not found: {target_id}")

    target.update(patch)

    # Server-controlled edited flag: any patch to a leaf marks it as touched.
    # The patch itself can never contain `edited` (rejected upstream in
    # validate_patch_fields), so this is the only place it flips to true.
    if target.get("type") in _LEAF_TYPES_WITH_EDITED:
        target["edited"] = True

    return checklist
