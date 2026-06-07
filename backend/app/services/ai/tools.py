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
            "`targetContainerId` to the new component's `humanReadableId` — the server "
            "resolves that to the real id at apply time."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["targetContainerId", "component"],
            "properties": {
                "targetContainerId": {
                    "type": "string",
                    "description": (
                        "Real id, humanReadableId of a component added earlier in this batch, "
                        "or the literal root id provided in the system prompt."
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
                    "description": "Map of fields to overwrite. See docs/component-structure.md.",
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


# Lets the model set/rename the checklist's title and description. The id and
# url live on the DB row (not in the tree JSON), so the AI service tracks the
# proposed values on the run result; the route applies them on commit.
UPDATE_CHECKLIST_METADATA_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "update_checklist_metadata",
        "description": (
            "Set or rename the checklist's title and/or description. Call this "
            "ONCE early in the conversation when the user describes what the "
            "checklist is about, so the title reflects the real subject "
            "(replacing placeholders like 'Untitled checklist'). Only call again "
            "if the user explicitly asks to rename."
        ),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {
                    "type": "string",
                    "description": "New checklist title (short, descriptive).",
                },
                "description": {
                    "type": "string",
                    "description": "Optional one-sentence description of the checklist.",
                },
            },
        },
    },
}


ALL_TOOLS: list[dict] = [
    ADD_COMPONENT_TOOL,
    UPDATE_COMPONENT_TOOL,
    DELETE_COMPONENT_TOOL,
    UPDATE_CHECKLIST_METADATA_TOOL,
]

# For "create from text" the checklist starts empty and the AI is building it.
# It can also name it via the metadata tool.
CREATE_TOOLS: list[dict] = [ADD_COMPONENT_TOOL, UPDATE_CHECKLIST_METADATA_TOOL]


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
# vision-specific image attachment tool + metadata.
OBSERVE_TOOLS: list[dict] = [
    ADD_IMAGE_TO_BLOCK_TOOL,
    UPDATE_COMPONENT_TOOL,
    DELETE_COMPONENT_TOOL,
    UPDATE_CHECKLIST_METADATA_TOOL,
]
