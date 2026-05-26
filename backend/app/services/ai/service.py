"""
AI orchestration: prompt → tool calls → ChecklistOperations → checklist JSON.

Two public entry points:

- `generate_checklist_from_text(prompt)` builds a brand-new checklist from a
  natural-language description.
- `edit_checklist_with_ai(checklist, instruction)` mutates an existing
  checklist in-place.

Both functions use a MULTI-TURN tool-call loop: each round, the model emits
tool calls, the server applies them through the regular validation pipeline
(`apply_checklist_operations`), and the new component ids are fed back so the
model can reference them in the next round. The loop ends when the model stops
calling tools (i.e. it considers the task complete) or hits the round cap.

The validators in `app.services.checklist_update.*` are the same ones manual
edits use — bad model output is rejected the same way a malformed frontend
payload would be.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.schemas.checklist_operations import (
    AddComponentOperation,
    DeleteComponentOperation,
    UpdateComponentOperation,
)
from app.services.ai.openai_client import OpenAIClient, ToolCall
from app.services.ai.prompts import build_create_system_prompt, build_edit_system_prompt
from app.services.ai.tools import ALL_TOOLS, CREATE_TOOLS
from app.services.checklist_update.exceptions import ChecklistOperationError
from app.services.checklist_update.service import apply_checklist_operations
from app.services.checklist_update.tree_utils import find_component_by_id


@dataclass
class AIRunResult:
    """Detailed report from one AI run — useful for debugging in the test script."""
    checklist: dict
    applied_calls: int = 0
    skipped_calls: list[dict] = field(default_factory=list)
    raw_tool_calls: list[dict] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _find_by_human_readable_id(node: dict, hrid: str) -> dict | None:
    if node.get("humanReadableId") == hrid:
        return node
    for key in ("children", "items"):
        for child in node.get(key, []) or []:
            if isinstance(child, dict):
                found = _find_by_human_readable_id(child, hrid)
                if found is not None:
                    return found
    return None


def _resolve_target_container_id(checklist: dict, target_ref: str) -> str:
    """
    The model may reference a parent container either by its real id or by the
    `humanReadableId` of something it added earlier. Try humanReadableId first;
    if no match, fall through and let the downstream validator decide whether
    the ref is a real id.
    """
    found = _find_by_human_readable_id(checklist, target_ref)
    if found is not None:
        return found["id"]
    return target_ref


def _find_checkbox_groups(node: dict, acc: list[dict] | None = None) -> list[dict]:
    """Collect every checkboxGroup in the tree (used to suggest fixes to the model)."""
    if acc is None:
        acc = []
    if node.get("type") == "checkboxGroup":
        acc.append(node)
    for key in ("children", "items"):
        for child in node.get(key, []) or []:
            if isinstance(child, dict):
                _find_checkbox_groups(child, acc)
    return acc


def _build_hint_for_failure(call: ToolCall, checklist: dict, exc: Exception) -> str | None:
    """
    Turn certain frequent model mistakes into actionable hints we feed back as
    part of the tool reply. The model usually corrects on the next round once
    it sees a concrete suggestion.
    """
    # Case: tried to add a checkbox somewhere that isn't a checkboxGroup.
    if (
        call.name == "add_component"
        and call.arguments.get("component", {}).get("type") == "checkbox"
        and "checkboxGroup" in str(exc)
    ):
        groups = _find_checkbox_groups(checklist)
        if groups:
            refs = ", ".join(
                f"{g.get('humanReadableId') or g['id']!r}" for g in groups[-3:]
            )
            return (
                "checkbox items can only go inside a checkboxGroup. Existing "
                f"checkboxGroups you can target: {refs}. If none of these are "
                "the right group, FIRST call add_component to create a new "
                "checkboxGroup (give it a humanReadableId), THEN add the "
                "checkbox with targetContainerId set to that group."
            )
        return (
            "checkbox items can only go inside a checkboxGroup. No checkboxGroup "
            "exists yet — call add_component to create one (with a "
            "humanReadableId), then add the checkbox into it."
        )
    return None


def _build_callback(result: AIRunResult):
    """
    Build the `on_tool_call` callback the OpenAI client invokes for each tool
    call. The callback applies the call via the regular operation pipeline,
    updates `result`, and returns a JSON-serialisable outcome that's fed back
    to the model so it can reference newly-created ids.
    """

    def on_tool_call(call: ToolCall) -> dict:
        result.raw_tool_calls.append({"name": call.name, "arguments": call.arguments})
        args = call.arguments

        try:
            if call.name == "add_component":
                target = _resolve_target_container_id(result.checklist, args["targetContainerId"])
                op = AddComponentOperation.model_construct(
                    operation="addComponent",
                    targetContainerId=target,
                    component=args["component"],
                    position=args.get("position", "end"),
                )
            elif call.name == "update_component":
                op = UpdateComponentOperation.model_construct(
                    operation="updateComponent",
                    targetId=args["targetId"],
                    patch=args["patch"],
                )
            elif call.name == "delete_component":
                op = DeleteComponentOperation.model_construct(
                    operation="deleteComponent",
                    targetId=args["targetId"],
                )
            else:
                reason = f"unknown tool {call.name!r}"
                result.skipped_calls.append({"call": {"name": call.name, "arguments": args}, "reason": reason})
                return {"ok": False, "error": reason}

            result.checklist = apply_checklist_operations(result.checklist, [op])
            result.applied_calls += 1

        except (ChecklistOperationError, KeyError, TypeError) as exc:
            reason = f"{type(exc).__name__}: {exc}"
            result.skipped_calls.append({"call": {"name": call.name, "arguments": args}, "reason": reason})
            hint = _build_hint_for_failure(call, result.checklist, exc)
            response: dict[str, Any] = {"ok": False, "error": reason}
            if hint:
                response["hint"] = hint
            return response

        # On success, hand back something useful to the model.
        if call.name == "add_component":
            hrid = args.get("component", {}).get("humanReadableId")
            added = _find_by_human_readable_id(result.checklist, hrid) if hrid else None
            return {
                "ok": True,
                "id": added["id"] if added else None,
                "humanReadableId": hrid,
            }
        if call.name == "update_component":
            return {"ok": True, "updated_id": args.get("targetId")}
        if call.name == "delete_component":
            return {"ok": True, "deleted_id": args.get("targetId")}
        return {"ok": True}

    return on_tool_call


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

def generate_checklist_from_text(
    prompt: str,
    *,
    title: str | None = None,
    description: str | None = None,
    max_rounds: int = 5,
) -> AIRunResult:
    """
    Build a brand-new checklist tree from a natural-language description.

    Returns an AIRunResult whose `.checklist` field is the final JSON tree,
    ready to persist via the regular `create_checklist_for_user` service.
    """
    root_id = f"root_{uuid.uuid4().hex[:12]}"
    checklist: dict[str, Any] = {
        "id": root_id,
        "type": "checklist",
        "title": title,
        "description": description,
        "children": [],
    }

    result = AIRunResult(checklist=checklist)
    on_tool_call = _build_callback(result)

    system_prompt = build_create_system_prompt(root_id)
    user_prompt = (
        f"Build a checklist for:\n\n{prompt}\n\n"
        f"The root container id is `{root_id}`. Use it as `targetContainerId` "
        f"for the top-level sections, then fill every section with the "
        f"appropriate fields and checkbox items. Keep going until done."
    )

    client = OpenAIClient()
    client.chat_with_tools(
        system_prompt,
        user_prompt,
        CREATE_TOOLS,
        on_tool_call,
        max_rounds=max_rounds,
    )

    return result


def edit_checklist_with_ai(
    checklist: dict,
    instruction: str,
    *,
    max_rounds: int = 4,
) -> AIRunResult:
    """
    Apply a natural-language edit instruction to an existing checklist JSON.

    The caller is responsible for:
    - snapshotting `checklist` into `checklist_prev` for undo
    - persisting `result.checklist` back to the DB
    """
    result = AIRunResult(checklist=checklist)
    on_tool_call = _build_callback(result)

    system_prompt = build_edit_system_prompt()
    user_prompt = (
        f"Current checklist JSON:\n```json\n{json.dumps(checklist, indent=2)}\n```\n\n"
        f"User instruction:\n{instruction}"
    )

    client = OpenAIClient()
    client.chat_with_tools(
        system_prompt,
        user_prompt,
        ALL_TOOLS,
        on_tool_call,
        max_rounds=max_rounds,
    )

    return result


# Re-export helper so callers don't have to dig through tree_utils.
__all__ = [
    "AIRunResult",
    "edit_checklist_with_ai",
    "find_component_by_id",
    "generate_checklist_from_text",
]
