"""
Standalone smoke / demonstration script for the checklist update service.

Run from the `backend/` directory:

    python test_add_delete_update.py

It walks through:
  1. Adding every component type (section, textField, numberField, imageBlock,
     table, checkboxGroup, checkbox).
  2. Updating fields of each type.
  3. Deleting a component.
  4. Triggering each of the validation errors the handlers should reject.

If everything passes you see a summary at the bottom and the final checklist
JSON dump. If anything regresses the script exits with a non-zero status.

No pytest, no fixtures, no extra files needed — pure stdlib + the project's own
modules.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any

# Make `from app...` resolvable when running this file directly from backend/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.schemas.checklist_operations import (  # noqa: E402
    AddComponentOperation,
    DeleteComponentOperation,
    UpdateComponentOperation,
)
from app.services.checklist_update.exceptions import (  # noqa: E402
    ComponentNotFoundError,
    InvalidComponentPayloadError,
    InvalidTargetContainerError,
)
from app.services.checklist_update.service import apply_checklist_operations  # noqa: E402
from app.services.checklist_update.tree_utils import find_component_by_id  # noqa: E402


# --------------------------------------------------------------------------- #
# Tiny test harness                                                            #
# --------------------------------------------------------------------------- #

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def step(name: str):
    """Decorator that runs a function as a labelled test step."""
    def wrap(fn):
        try:
            fn()
            PASSED.append(name)
            print(f"  [OK]   {name}")
        except Exception as exc:  # noqa: BLE001
            FAILED.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"  [FAIL] {name}")
            traceback.print_exc()
        return fn
    return wrap


def expect_error(name: str, expected_exc: type[Exception], fn):
    """Run `fn`, expecting it to raise `expected_exc`."""
    try:
        fn()
    except expected_exc as exc:
        PASSED.append(name)
        print(f"  [OK]   {name}  (raised {type(exc).__name__})")
        return
    except Exception as exc:  # noqa: BLE001
        FAILED.append((name, f"raised {type(exc).__name__} instead of {expected_exc.__name__}: {exc}"))
        print(f"  [FAIL] {name}  -- wrong exception type")
        return
    FAILED.append((name, f"expected {expected_exc.__name__}, nothing raised"))
    print(f"  [FAIL] {name}  -- no exception raised")


def assert_eq(actual: Any, expected: Any, msg: str = "") -> None:
    if actual != expected:
        raise AssertionError(f"{msg}: expected {expected!r}, got {actual!r}")


# --------------------------------------------------------------------------- #
# Fresh root document                                                          #
# --------------------------------------------------------------------------- #

ROOT_ID = "root-checklist-0001"


def fresh_root() -> dict:
    return {"id": ROOT_ID, "type": "checklist", "children": []}


def apply(checklist: dict, op_dict: dict) -> dict:
    """
    Build an operation object and apply it.

    We use `model_construct` instead of regular `Model(**kwargs)` because the
    schema declares `component: AddComponentPayload | dict[str, Any]` and pydantic
    eagerly coerces the dict into `AddComponentPayload` (which only declares
    `type`), stripping every other field. `model_construct` skips validation and
    preserves the raw dict, which is what the handlers expect.
    """
    op_type = op_dict["operation"]
    if op_type == "addComponent":
        op = AddComponentOperation.model_construct(
            operation="addComponent",
            targetContainerId=op_dict["targetContainerId"],
            component=op_dict["component"],
            position=op_dict.get("position", "end"),
        )
    elif op_type == "updateComponent":
        op = UpdateComponentOperation.model_construct(
            operation="updateComponent",
            targetId=op_dict["targetId"],
            patch=op_dict["patch"],
        )
    elif op_type == "deleteComponent":
        op = DeleteComponentOperation.model_construct(
            operation="deleteComponent",
            targetId=op_dict["targetId"],
        )
    else:
        raise ValueError(f"unknown op {op_type}")
    return apply_checklist_operations(checklist, [op])


# --------------------------------------------------------------------------- #
# Happy-path scenario: add every component, then update / delete some          #
# --------------------------------------------------------------------------- #

print("\n=== Happy path ===")

checklist = fresh_root()


@step("add section under root")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "addComponent",
            "targetContainerId": ROOT_ID,
            "component": {
                "type": "section",
                "label": "Safety",
                "humanReadableId": "section_safety",
            },
        },
    )
    section = checklist["children"][0]
    assert_eq(section["type"], "section", "section type")
    assert_eq(section["label"], "Safety", "section label")
    assert section["id"].startswith("sec_"), "id prefix"


SECTION_ID = checklist["children"][0]["id"]


@step("add textField under section")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "addComponent",
            "targetContainerId": SECTION_ID,
            "component": {
                "type": "textField",
                "label": "Inspector Name",
                "placeholder": "Full name",
                "required": True,
            },
        },
    )
    field = checklist["children"][0]["children"][0]
    assert_eq(field["type"], "textField", "textField type")
    assert_eq(field["value"], "", "textField default value")
    assert_eq(field["required"], True, "textField required")
    assert field["id"].startswith("field_"), "id prefix"


@step("add numberField under section")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "addComponent",
            "targetContainerId": SECTION_ID,
            "component": {
                "type": "numberField",
                "label": "Temperature",
                "unit": "C",
                "min": -20,
                "max": 60,
            },
        },
    )
    field = checklist["children"][0]["children"][1]
    assert_eq(field["type"], "numberField", "numberField type")
    assert_eq(field["unit"], "C", "numberField unit")
    assert_eq(field["min"], -20, "numberField min")


@step("add imageBlock under section")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "addComponent",
            "targetContainerId": SECTION_ID,
            "component": {
                "type": "imageBlock",
                "label": "Reference photos",
                "allowUpload": True,
                "images": [
                    {
                        "imageId": "img-001",
                        "url": "/api/images/img-001",
                        "caption": "PPE example",
                    }
                ],
            },
        },
    )
    block = checklist["children"][0]["children"][2]
    assert_eq(block["type"], "imageBlock", "imageBlock type")
    assert_eq(len(block["images"]), 1, "imageBlock image count")
    assert_eq(block["allowUpload"], True, "imageBlock allowUpload")


@step("add table under section")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "addComponent",
            "targetContainerId": SECTION_ID,
            "component": {
                "type": "table",
                "label": "Equipment log",
                "columns": [
                    {"id": "col-name", "label": "Equipment", "type": "text"},
                    {"id": "col-days", "label": "Days since service", "type": "number"},
                    {"id": "col-ok", "label": "OK", "type": "checkbox"},
                ],
                "rows": [
                    {
                        "id": "row-1",
                        "cells": {"col-name": "Extinguisher", "col-days": 42, "col-ok": True},
                    }
                ],
            },
        },
    )
    table = checklist["children"][0]["children"][3]
    assert_eq(table["type"], "table", "table type")
    assert_eq(len(table["columns"]), 3, "table column count")
    assert_eq(table["rows"][0]["cells"]["col-name"], "Extinguisher", "table cell text")


@step("add checkboxGroup under section")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "addComponent",
            "targetContainerId": SECTION_ID,
            "component": {"type": "checkboxGroup", "label": "PPE"},
        },
    )
    group = checklist["children"][0]["children"][4]
    assert_eq(group["type"], "checkboxGroup", "checkboxGroup type")
    assert_eq(group["items"], [], "checkboxGroup items default")


GROUP_ID = checklist["children"][0]["children"][4]["id"]


@step("add two checkbox items under checkboxGroup")
def _():
    global checklist
    for label in ("Hard hat", "Boots"):
        checklist = apply(
            checklist,
            {
                "operation": "addComponent",
                "targetContainerId": GROUP_ID,
                "component": {"type": "checkbox", "label": label},
            },
        )
    items = find_component_by_id(checklist, GROUP_ID)["items"]
    assert_eq(len(items), 2, "checkbox count")
    assert_eq(items[0]["checked"], False, "checkbox default")


# Capture ids generated above for later operations.
TEXT_FIELD_ID = checklist["children"][0]["children"][0]["id"]
NUMBER_FIELD_ID = checklist["children"][0]["children"][1]["id"]
IMAGE_BLOCK_ID = checklist["children"][0]["children"][2]["id"]
TABLE_ID = checklist["children"][0]["children"][3]["id"]
FIRST_CHECKBOX_ID = find_component_by_id(checklist, GROUP_ID)["items"][0]["id"]
SECOND_CHECKBOX_ID = find_component_by_id(checklist, GROUP_ID)["items"][1]["id"]


print("\n=== Updates ===")


@step("update section label + collapsed")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": SECTION_ID,
            "patch": {"label": "Safety checks", "collapsed": True},
        },
    )
    section = find_component_by_id(checklist, SECTION_ID)
    assert_eq(section["label"], "Safety checks", "section label")
    assert_eq(section["collapsed"], True, "section collapsed")


@step("update textField value")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": TEXT_FIELD_ID,
            "patch": {"value": "Alice"},
        },
    )
    assert_eq(find_component_by_id(checklist, TEXT_FIELD_ID)["value"], "Alice", "textField value")


@step("update numberField value")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": NUMBER_FIELD_ID,
            "patch": {"value": 23.5},
        },
    )
    assert_eq(find_component_by_id(checklist, NUMBER_FIELD_ID)["value"], 23.5, "numberField value")


@step("update imageBlock images list")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": IMAGE_BLOCK_ID,
            "patch": {
                "images": [
                    {"imageId": "img-002", "url": "/api/images/img-002", "caption": None},
                ],
            },
        },
    )
    images = find_component_by_id(checklist, IMAGE_BLOCK_ID)["images"]
    assert_eq(len(images), 1, "imageBlock image count")
    assert_eq(images[0]["imageId"], "img-002", "imageBlock image id")


@step("update table rows (cells re-validated against existing columns)")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": TABLE_ID,
            "patch": {
                "rows": [
                    {
                        "id": "row-1",
                        "cells": {"col-name": "Extinguisher A", "col-days": 10, "col-ok": True},
                    },
                    {
                        "id": "row-2",
                        "cells": {"col-name": "First Aid Kit", "col-days": 4, "col-ok": False},
                    },
                ]
            },
        },
    )
    table = find_component_by_id(checklist, TABLE_ID)
    assert_eq(len(table["rows"]), 2, "table row count")
    assert_eq(table["rows"][1]["cells"]["col-name"], "First Aid Kit", "table cell text")


@step("update checkboxGroup label")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": GROUP_ID,
            "patch": {"label": "PPE checks"},
        },
    )
    assert_eq(find_component_by_id(checklist, GROUP_ID)["label"], "PPE checks", "group label")


@step("update checkbox checked=true")
def _():
    global checklist
    checklist = apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": FIRST_CHECKBOX_ID,
            "patch": {"checked": True},
        },
    )
    assert_eq(find_component_by_id(checklist, FIRST_CHECKBOX_ID)["checked"], True, "checkbox checked")


print("\n=== Deletes ===")


@step("delete one checkbox")
def _():
    global checklist
    checklist = apply(
        checklist,
        {"operation": "deleteComponent", "targetId": SECOND_CHECKBOX_ID},
    )
    items = find_component_by_id(checklist, GROUP_ID)["items"]
    assert_eq(len(items), 1, "checkbox count after delete")
    assert find_component_by_id(checklist, SECOND_CHECKBOX_ID) is None, "deleted id is gone"


# --------------------------------------------------------------------------- #
# Negative tests — these must raise the documented exceptions                  #
# --------------------------------------------------------------------------- #

print("\n=== Validation failures ===")

expect_error(
    "checkbox cannot be added outside a checkboxGroup",
    InvalidTargetContainerError,
    lambda: apply(
        checklist,
        {
            "operation": "addComponent",
            "targetContainerId": SECTION_ID,  # section, not a group
            "component": {"type": "checkbox", "label": "Stray"},
        },
    ),
)

expect_error(
    "unknown field in add payload is rejected",
    InvalidComponentPayloadError,
    lambda: apply(
        checklist,
        {
            "operation": "addComponent",
            "targetContainerId": SECTION_ID,
            "component": {"type": "textField", "label": "X", "wat": 1},
        },
    ),
)

expect_error(
    "min > max is rejected on numberField add",
    InvalidComponentPayloadError,
    lambda: apply(
        checklist,
        {
            "operation": "addComponent",
            "targetContainerId": SECTION_ID,
            "component": {"type": "numberField", "label": "Bad", "min": 10, "max": 1},
        },
    ),
)

expect_error(
    "cannot patch 'type'",
    InvalidComponentPayloadError,
    lambda: apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": TEXT_FIELD_ID,
            "patch": {"type": "numberField"},
        },
    ),
)

expect_error(
    "cannot patch 'id'",
    InvalidComponentPayloadError,
    lambda: apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": TEXT_FIELD_ID,
            "patch": {"id": "evil"},
        },
    ),
)

expect_error(
    "cannot patch unsupported field on checkbox",
    InvalidComponentPayloadError,
    lambda: apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": FIRST_CHECKBOX_ID,
            "patch": {"value": "nope"},  # value is a textField field, not checkbox
        },
    ),
)

expect_error(
    "table cell type mismatch is rejected",
    InvalidComponentPayloadError,
    lambda: apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": TABLE_ID,
            "patch": {
                "rows": [
                    {
                        "id": "row-bad",
                        "cells": {"col-days": "not-a-number"},
                    }
                ]
            },
        },
    ),
)

expect_error(
    "update on missing id raises ComponentNotFoundError",
    ComponentNotFoundError,
    lambda: apply(
        checklist,
        {
            "operation": "updateComponent",
            "targetId": "does-not-exist",
            "patch": {"label": "x"},
        },
    ),
)


# --------------------------------------------------------------------------- #
# Summary + final checklist dump                                               #
# --------------------------------------------------------------------------- #

print("\n=== Final checklist ===")
print(json.dumps(checklist, indent=2))

print("\n=== Summary ===")
print(f"  passed: {len(PASSED)}")
print(f"  failed: {len(FAILED)}")
for name, reason in FAILED:
    print(f"    - {name}: {reason}")

sys.exit(0 if not FAILED else 1)
