from typing import Any

from app.services.checklist_update.exceptions import CannotDeleteRootError, ComponentNotFoundError, InvalidTargetContainerError


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

    # TODO: later constrain allowed patch fields per component type.
    target.update(patch)
    return checklist
