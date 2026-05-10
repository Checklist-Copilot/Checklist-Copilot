from copy import deepcopy

from fastapi import HTTPException


def find_section(checklist: dict, section_uid: str) -> dict | None:
    for section in checklist.get("sections", []):
        if section.get("uid") == section_uid:
            return section

    return None


def find_item(checklist: dict, item_uid: str) -> dict | None:
    for section in checklist.get("sections", []):
        for item in section.get("items", []):
            if item.get("uid") == item_uid:
                return item

    return None


def apply_operations(checklist: dict, operations: list[dict]) -> dict:
    updated = deepcopy(checklist)

    for operation in operations:
        operation_type = operation.get("type")

        if operation_type == "add_section":
            section = operation["payload"]["section"]
            updated.setdefault("sections", []).append(section)

        elif operation_type == "add_item":
            section_uid = operation["target_uid"]
            section = find_section(updated, section_uid)

            if section is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Section {section_uid} not found",
                )

            item = operation["payload"]["item"]
            section.setdefault("items", []).append(item)

        elif operation_type == "update_item":
            item_uid = operation["target_uid"]
            item = find_item(updated, item_uid)

            if item is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item {item_uid} not found",
                )

            item.update(operation["payload"])

        elif operation_type == "delete_item":
            item_uid = operation["target_uid"]
            deleted = False

            for section in updated.get("sections", []):
                old_items = section.get("items", [])
                new_items = [
                    item for item in old_items
                    if item.get("uid") != item_uid
                ]

                if len(new_items) != len(old_items):
                    deleted = True

                section["items"] = new_items

            if not deleted:
                raise HTTPException(
                    status_code=400,
                    detail=f"Item {item_uid} not found",
                )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown operation type: {operation_type}",
            )

    return updated
