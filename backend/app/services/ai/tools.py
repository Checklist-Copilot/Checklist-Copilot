"""
JSON-schema definitions for the OpenAI tools the model can invoke.

There is one tool per operation type (add / update / delete). Each tool's
parameters mirror the corresponding pydantic operation in
`app.schemas.checklist_operations`, so a successful tool call drops directly
into `apply_checklist_operations`.

The `component` field on `add_component` is intentionally loose (free-form
object) — the per-type field specs are enforced by the validators in
`app.services.checklist_update.add.*`, so we don't try to encode all seven
component shapes here.
"""
from __future__ import annotations


_COMPONENT_TYPES = ["section", "checkboxGroup", "checkbox", "textField", "numberField", "imageBlock", "table"]


ADD_COMPONENT_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "add_component",
        "description": (
            "Add a new component to the checklist tree. "
            "Use this for every new section, field, checkbox, image block, or table. "
            "When you need to nest a component inside one you just created, set "
            "`targetContainerId` to the real `id` returned by the previous "
            "tool response. Do not use `humanReadableId` as a target."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["targetContainerId", "component"],
            "properties": {
                "targetContainerId": {
                    "type": "string",
                    "description": (
                        "Real component id returned by an earlier tool response, "
                        "or the literal root id provided in the system prompt. "
                        "Do not use humanReadableId here."
                    ),
                },
                "position": {
                    "type": "string",
                    "enum": ["start", "end"],
                    "description": "Where to insert inside the container. Defaults to 'end'.",
                },
                "component": {
                    "type": "object",
                    "description": (
                        "The component to add. Must include `type` (one of "
                        f"{_COMPONENT_TYPES}) and `label`. May include `humanReadableId` "
                        "and any other fields documented in docs/component-structure.md."
                    ),
                    "required": ["type", "label"],
                    "properties": {
                        "type": {"type": "string", "enum": _COMPONENT_TYPES},
                        "label": {"type": "string"},
                        "humanReadableId": {"type": "string"},
                    },
                    # Per-type extra fields (collapsed, checked, columns, …) are
                    # validated by the backend handlers — leave the schema open.
                    "additionalProperties": True,
                },
            },
        },
    },
}


UPDATE_COMPONENT_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "update_component",
        "description": (
            "Patch fields on an existing component (e.g. tick a checkbox, fill in a "
            "textField's `value`, change a label). Cannot change `type` or `id`."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["targetId", "patch"],
            "properties": {
                "targetId": {
                    "type": "string",
                    "description": "Real id of the component to update.",
                },
                "patch": {
                    "type": "object",
                    "description": (
                        "Map of fields to overwrite. For table-specific edits, send "
                        "`tableAction` as one of `newRow`, `deleteRow`, `newColumn`, "
                        "`deleteColumn`, or `cell`. For `deleteRow`/`deleteColumn`, "
                        "the update_component `targetId` must always be the table component id. "
                        "For `deleteRow`/`deleteColumn`, include patch.`targetId` with the row id or column id. For `cell`, "
                        "include `rowId`, `columnId`, and `value`; number cells require "
                        "a JSON number or null. For `newRow`/`newColumn`, the backend "
                        "creates blank values and ids."
                    ),
                    "additionalProperties": True,
                },
            },
        },
    },
}


DELETE_COMPONENT_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "delete_component",
        "description": "Remove a component (and its children) from the checklist tree.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["targetId"],
            "properties": {
                "targetId": {"type": "string", "description": "Real id of the component to delete."},
            },
        },
    },
}


ALL_TOOLS: list[dict] = [ADD_COMPONENT_TOOL, UPDATE_COMPONENT_TOOL, DELETE_COMPONENT_TOOL]

# For "create from text" we don't need update/delete — the checklist starts empty.
CREATE_TOOLS: list[dict] = [ADD_COMPONENT_TOOL]


# --------------------------------------------------------------------------- #
# Vision-mode tool                                                             #
# --------------------------------------------------------------------------- #

# Used only by the /observe endpoint. The image's id and url come from the
# request context (the user already uploaded the image), so the model only
# decides WHICH imageBlock to attach it to and provides a short caption.
# The server appends the new entry to the imageBlock's `images` array — the
# model doesn't have to reproduce existing entries.
ADD_IMAGE_TO_BLOCK_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "add_image_to_block",
        "description": (
            "Attach the user's current image to an existing imageBlock in the "
            "checklist. Pick the imageBlock whose label best matches what the "
            "image shows. Only call this when the user wants the image added, "
            "or when you are confident it belongs in a specific imageBlock. "
            "The image id and URL are supplied by the server — you do not need "
            "to pass them."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["targetBlockId", "caption"],
            "properties": {
                "targetBlockId": {
                    "type": "string",
                    "description": "Real id of the target imageBlock component.",
                },
                "caption": {
                    "type": "string",
                    "description": "Short caption describing what the image shows.",
                },
            },
        },
    },
}

# Tool set exposed to the model during the vision flow: regular edit ops + the
# vision-specific image attachment tool.
OBSERVE_TOOLS: list[dict] = [
    ADD_IMAGE_TO_BLOCK_TOOL,
    UPDATE_COMPONENT_TOOL,
    DELETE_COMPONENT_TOOL,
]
