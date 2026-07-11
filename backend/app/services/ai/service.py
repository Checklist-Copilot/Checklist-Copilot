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
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

from app.schemas.checklist_operations import (
    AddComponentOperation,
    DeleteComponentOperation,
    UpdateComponentOperation,
)
from app.services.ai.openai_client import OpenAIClient, ToolCall
from app.services.ai.prompts import (
    build_create_system_prompt,
    build_edit_system_prompt,
    build_observe_system_prompt,
)
from app.services.ai.tools import ALL_TOOLS, CREATE_TOOLS, OBSERVE_TOOLS
from app.services.ai.use_mode_guard import AiChecklistMode, validate_use_mode_tool_call
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
    # The model's natural-language message to the user (its "speech" channel).
    # Surfaced to the frontend so the AI can talk back, not just mutate the tree.
    reply: str = ""


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


def _collect_component_ids(node: dict, acc: set[str] | None = None) -> set[str]:
    """Collect component ids so add_component can report the real generated id."""
    if acc is None:
        acc = set()
    node_id = node.get("id")
    if isinstance(node_id, str):
        acc.add(node_id)
    for key in ("children", "items"):
        for child in node.get(key, []) or []:
            if isinstance(child, dict):
                _collect_component_ids(child, acc)
    return acc


def _find_first_new_component_id(checklist: dict, previous_ids: set[str]) -> str | None:
    """Return the parent component id that appeared after a successful add operation."""
    node_id = checklist.get("id")
    if isinstance(node_id, str) and node_id not in previous_ids:
        return node_id
    for key in ("children", "items"):
        for child in checklist.get(key, []) or []:
            if isinstance(child, dict):
                found = _find_first_new_component_id(child, previous_ids)
                if found is not None:
                    return found
    return None


def _resolve_target_container_id(checklist: dict, target_ref: str) -> str:
    """
    Resolve a target container reference before validation.

    Prompts instruct the model to use real ids. The humanReadableId fallback is
    kept only as a compatibility guard for older prompts or in-flight clients.
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
            refs = ", ".join(f"{g['id']!r}" for g in groups[-3:])
            return (
                "checkbox items can only go inside a checkboxGroup. Existing "
                f"checkboxGroups you can target by real id: {refs}. If none of these are "
                "the right group, FIRST call add_component to create a new "
                "checkboxGroup, THEN add the checkbox with targetContainerId "
                "set to the real id returned by that tool response."
            )
        return (
            "checkbox items can only go inside a checkboxGroup. No checkboxGroup "
            "exists yet — call add_component to create one, then use the real "
            "id returned by that tool response as targetContainerId."
        )
    return None


# Component types where a same-type, same-label sibling inside the same
# container is (almost) always an accidental re-add rather than an
# intentional duplicate — e.g. a model that nests a field inline via a
# section's `children` and then separately re-adds it in a later round.
# `section` is deliberately excluded: users may legitimately want two
# sections with the same name.
_DEDUPLICATE_ON_REPEAT_TYPES = {
    "checkboxGroup", "checkbox", "textField", "numberField", "imageBlock", "table",
}


def _find_existing_component(checklist: dict, container_id: str, component_type: str, label: str) -> dict | None:
    """
    Look for a component of `component_type` with a matching (trimmed,
    case-insensitive) label already inside `container_id`. Used to stop the
    model from creating duplicate components in the same container — e.g.
    across tool-call rounds, or when it both nests a field inline in a
    section's `children` and separately re-adds it.
    """
    container = find_component_by_id(checklist, container_id)
    if container is None:
        return None
    target_label = label.strip().lower()
    for key in ("children", "items"):
        for child in container.get(key, []) or []:
            if (
                isinstance(child, dict)
                and child.get("type") == component_type
                and (child.get("label") or "").strip().lower() == target_label
            ):
                return child
    return None


def _build_callback(result: AIRunResult, mode: AiChecklistMode = "edit"):
    """
    Build the `on_tool_call` callback the OpenAI client invokes for each tool
    call. It enforces use-mode permissions before applying allowed calls via
    the regular operation pipeline.
    """

    def on_tool_call(call: ToolCall) -> dict:
        result.raw_tool_calls.append({"name": call.name, "arguments": call.arguments})
        args = call.arguments
        if mode == "use":
            guard = validate_use_mode_tool_call(result.checklist, call)
            if not guard.allowed:
                reason = guard.reason or "This tool call is not allowed in use mode."
                result.skipped_calls.append({"call": {"name": call.name, "arguments": args}, "reason": reason})
                return {
                    "ok": False,
                    "error": reason,
                    "hint": (
                        "Tell the user this cannot be done because the checklist is in USE MODE. "
                        "Use mode only permits updating existing user-entered values, existing "
                        "table cells, and image attachments. Do not add/delete components or "
                        "table rows/columns."
                    ),
                }
        table_action_context: dict[str, Any] | None = None

        try:
            if call.name == "add_component":
                target = _resolve_target_container_id(result.checklist, args["targetContainerId"])
                component = args.get("component", {})
                component_ids_before_add = _collect_component_ids(result.checklist)

                # Idempotency: the model sometimes re-creates a component it
                # already added earlier — either in an earlier round, or via
                # a section's inline `children` followed by a separate
                # add_component call for the same field. Reuse the existing
                # one instead of creating a duplicate.
                component_type = component.get("type")
                if component_type in _DEDUPLICATE_ON_REPEAT_TYPES:
                    existing_component = _find_existing_component(
                        result.checklist, target, component_type, component.get("label", "")
                    )
                    if existing_component is not None:
                        return {
                            "ok": True,
                            "id": existing_component["id"],
                            "humanReadableId": existing_component.get("humanReadableId"),
                            "already_exists": True,
                            "message": (
                                f"A {component_type} with this label already exists in this "
                                f"container — reusing it instead of creating a duplicate. Use "
                                f"targetContainerId={existing_component['id']!r} if you need to "
                                "nest something inside it. Do not use humanReadableId as a target."
                            ),
                        }

                op = AddComponentOperation.model_construct(
                    operation="addComponent",
                    targetContainerId=target,
                    component=args["component"],
                    position=args.get("position", "end"),
                )
            elif call.name == "update_component":
                target_id = args["targetId"]
                patch = args["patch"]
                if isinstance(patch, dict) and isinstance(patch.get("tableAction"), str):
                    target = find_component_by_id(result.checklist, target_id)
                    if target and target.get("type") == "table":
                        table_action_context = {
                            "action": patch.get("tableAction"),
                            "targetId": target_id,
                            "row_ids_before": [
                                row.get("id") for row in target.get("rows", []) if isinstance(row, dict)
                            ],
                            "column_ids_before": [
                                column.get("id") for column in target.get("columns", []) if isinstance(column, dict)
                            ],
                        }

                op = UpdateComponentOperation.model_construct(
                    operation="updateComponent",
                    targetId=target_id,
                    patch=patch,
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
            added_id = added["id"] if added else _find_first_new_component_id(
                result.checklist,
                component_ids_before_add,
            )
            return {
                "ok": True,
                "id": added_id,
                "humanReadableId": hrid,
                "message": "Use this returned real id for later targetContainerId values.",
            }
        if call.name == "update_component":
            if table_action_context:
                target = find_component_by_id(result.checklist, table_action_context["targetId"])
                rows = target.get("rows", []) if isinstance(target, dict) else []
                columns = target.get("columns", []) if isinstance(target, dict) else []
                row_ids_after = [row.get("id") for row in rows if isinstance(row, dict)]
                column_ids_after = [column.get("id") for column in columns if isinstance(column, dict)]
                added_row_ids = [row_id for row_id in row_ids_after if row_id not in table_action_context["row_ids_before"]]
                added_column_ids = [
                    column_id for column_id in column_ids_after if column_id not in table_action_context["column_ids_before"]
                ]

                return {
                    "ok": True,
                    "updated_id": args.get("targetId"),
                    "tableAction": table_action_context["action"],
                    "added_row_ids": added_row_ids,
                    "added_column_ids": added_column_ids,
                    "message": (
                        "For follow-up tableAction='cell' calls, keep targetId set to this table id. "
                        "Use the added row id as rowId. Do not use row ids as targetId."
                    ),
                }

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
    pdf_context: str | None = None,
    pdf_files: list[tuple[str, bytes]] | None = None,
    max_rounds: int = 10,
) -> AIRunResult:
    """
    Build a brand-new checklist tree from a natural-language description.

    `pdf_files` (filename, raw_bytes) attachments are sent directly to the
    model when provided, instead of the text-extraction `pdf_context` path.

    Returns an AIRunResult whose `.checklist` field is the final JSON tree,
    ready to persist via the regular `create_checklist_for_user` service.
    """
    root_id = "root"
    checklist: dict[str, Any] = {
        "id": root_id,
        "type": "root",
        "title": title,
        "description": description,
        "children": [],
    }

    result = AIRunResult(checklist=checklist)
    on_tool_call = _build_callback(result)

    system_prompt = build_create_system_prompt(root_id)

    pdf_context_rules = (
        "PDF CONTEXT GUIDANCE:\n"
        "- Treat the attached PDF document(s) as high-priority context for the user's goal.\n"
        "- Use their terminology, rules, requirements, headings, thresholds, and concrete "
        "values when they are relevant to the checklist.\n"
        "- The PDFs are guidance, not the only source of truth: you may also use the user's "
        "prompt and reasonable domain knowledge to make the checklist complete and usable.\n"
        "- Do not contradict the PDFs. If a PDF states a concrete requirement, represent it "
        "clearly as a checklist item, field, table column, or section.\n\n"
    )
    context_prefix = (
        f"The following text was extracted from a reference PDF document.\n\n"
        f"{pdf_context_rules}"
        f"PDF CONTENT:\n{pdf_context}\n\n---\n\n"
        if pdf_context
        else ""
    )
    user_prompt = (
        f"{context_prefix}"
        f"{'One or more PDF documents are attached to this message. ' + pdf_context_rules if pdf_files else ''}"
        f"Build a checklist for:\n\n{prompt}\n\n"
        f"The root container id is `{root_id}`. Use it as `targetContainerId` "
        f"for the top-level sections, then fill every section with the "
        f"appropriate fields and checkbox items. Keep going until done."
    )

    client = OpenAIClient()
    if pdf_files:
        chat_result = client.chat_with_tools_and_files(
            system_prompt,
            user_prompt,
            pdf_files,
            CREATE_TOOLS,
            on_tool_call,
            max_rounds=max_rounds,
        )
    else:
        chat_result = client.chat_with_tools(
            system_prompt,
            user_prompt,
            CREATE_TOOLS,
            on_tool_call,
            max_rounds=max_rounds,
        )
    result.reply = chat_result.reply

    return result


def generate_checklist_with_context(
    prompt: str,
    *,
    title: str | None = None,
    description: str | None = None,
    pdf_files: list[tuple[str, bytes]] | None = None,
) -> AIRunResult:
    """
    Generate a checklist from the user's prompt and optional PDF context files.
    The normal create prompt and tool loop are reused so PDFs only add context.
    """
    logger.info("Generating checklist with %d PDF attachment(s)", len(pdf_files or []))
    return generate_checklist_from_text(
        prompt,
        title=title,
        description=description,
        pdf_files=pdf_files,
    )


def review_checklist_with_ai(
    checklist: dict,
    *,
    pdf_files: list[tuple[str, bytes]] | None = None,
) -> str:
    """Review checklist quality using general knowledge and optional PDF context."""
    system_prompt = (
        "You are a senior checklist reviewer for a checklist-building app. Review "
        "the checklist for missing steps, unclear wording, weak validation points, "
        "and mismatches with any provided PDF context. Use the PDFs as high-priority "
        "context, but also use general domain knowledge. Do not modify the checklist.\n\n"
        "APP CAPABILITIES AND LIMITS:\n"
        "- The app can show sections, checkbox groups, checkboxes, text fields, number fields, image blocks, and tables.\n"
        "- Fields can be marked required and number fields can define min, max, unit, and value.\n"
        "- Tables can have text, number, and checkbox columns.\n"
        "- The app cannot do conditional logic, branching, formulas, dynamic visibility, automatic date validation, cross-field validation, workflows, approvals, reminders, or permissions.\n"
        "- If a best-practice idea needs unsupported behavior, translate it into something representable, such as an explicit checklist item, required field, section, table column, or instruction in a label.\n"
        "- Do not recommend features the app cannot implement unless you clearly phrase them as manual checklist wording.\n\n"
        "Return concise, actionable recommendations in markdown. Prioritize changes that can be applied with the available checklist components."
    )
    user_prompt = (
        "Review this checklist and suggest practical improvements. If PDFs are "
        "attached, compare the checklist against them and call out important gaps.\n\n"
        f"Checklist JSON:\n```json\n{json.dumps(checklist, indent=2)}\n```"
    )

    client = OpenAIClient()
    return client.complete_text(system_prompt, user_prompt, files=pdf_files)


def edit_checklist_with_ai(
    checklist: dict,
    instruction: str,
    *,
    mode: AiChecklistMode = "edit",
    max_rounds: int = 4,
) -> AIRunResult:
    """
    Apply a natural-language edit instruction to an existing checklist JSON.

    The caller is responsible for:
    - snapshotting `checklist` into `checklist_prev` for undo
    - persisting `result.checklist` back to the DB
    """
    result = AIRunResult(checklist=checklist)
    on_tool_call = _build_callback(result, mode)

    system_prompt = build_edit_system_prompt(mode)
    user_prompt = (
        f"Current checklist JSON:\n```json\n{json.dumps(checklist, indent=2)}\n```\n\n"
        f"User instruction:\n{instruction}"
    )

    client = OpenAIClient()
    chat_result = client.chat_with_tools(
        system_prompt,
        user_prompt,
        ALL_TOOLS,
        on_tool_call,
        max_rounds=max_rounds,
    )
    result.reply = chat_result.reply

    return result


# --------------------------------------------------------------------------- #
# Observe (vision) entry point                                                 #
# --------------------------------------------------------------------------- #

def _build_observe_callback(
    result: AIRunResult,
    image_id: str,
    image_url: str,
    mode: AiChecklistMode = "edit",
):
    """
    Callback for the vision flow. Handles `add_image_to_block` specially —
    the AI only provides the target block id and a caption; the server
    appends the new image entry (id + url) to the imageBlock's `images`
    list by emitting a regular `updateComponent` operation that goes
    through the standard validators.

    All other tool calls (`update_component`, `delete_component`) are
    delegated to the standard callback so the same code path handles them.
    """
    standard = _build_callback(result, mode)

    def on_tool_call(call: ToolCall) -> dict:
        if call.name != "add_image_to_block":
            return standard(call)

        result.raw_tool_calls.append({"name": call.name, "arguments": call.arguments})
        args = call.arguments
        if mode == "use":
            guard = validate_use_mode_tool_call(result.checklist, call)
            if not guard.allowed:
                reason = guard.reason or "This image tool call is not allowed in use mode."
                result.skipped_calls.append({"call": {"name": call.name, "arguments": args}, "reason": reason})
                return {"ok": False, "error": reason}
        try:
            target_block_id = args["targetBlockId"]
            caption = args.get("caption")
            if not isinstance(target_block_id, str) or not target_block_id:
                raise KeyError("targetBlockId must be a non-empty string")

            target = find_component_by_id(result.checklist, target_block_id)
            if target is None:
                raise ChecklistOperationError(f"component {target_block_id!r} not found")
            if target.get("type") != "imageBlock":
                raise ChecklistOperationError(
                    f"targetBlockId must point to an imageBlock, got {target.get('type')!r}"
                )

            existing = list(target.get("images") or [])

            # Idempotency: if this image is already attached to this block,
            # silently no-op and tell the model so it stops trying. Otherwise
            # an over-eager model would append duplicate entries (gpt-4o-mini
            # has been observed to call this tool twice for one image).
            already_attached = any(
                isinstance(img, dict) and img.get("imageId") == image_id
                for img in existing
            )
            if already_attached:
                return {
                    "ok": True,
                    "already_attached": True,
                    "added_to": target_block_id,
                    "image_id": image_id,
                    "message": (
                        "Image is already attached to this imageBlock. Do not "
                        "call add_image_to_block again for this image."
                    ),
                }

            new_entry = {
                "imageId": image_id,
                "url": image_url,
                "caption": caption if isinstance(caption, str) else None,
            }
            merged = existing + [new_entry]

            op = UpdateComponentOperation.model_construct(
                operation="updateComponent",
                targetId=target_block_id,
                patch={"images": merged},
            )
            result.checklist = apply_checklist_operations(result.checklist, [op])
            result.applied_calls += 1
            return {"ok": True, "added_to": target_block_id, "image_id": image_id}

        except (ChecklistOperationError, KeyError, TypeError) as exc:
            reason = f"{type(exc).__name__}: {exc}"
            result.skipped_calls.append(
                {"call": {"name": call.name, "arguments": args}, "reason": reason}
            )
            return {"ok": False, "error": reason}

    return on_tool_call


def observe_with_image(
    checklist: dict,
    instruction: str,
    *,
    image_id: str,
    image_url: str,
    image_data_url: str,
    prior_messages: list[dict] | None = None,
    mode: AiChecklistMode = "edit",
    max_rounds: int = 3,
) -> AIRunResult:
    """
    Vision flow: the user sends an instruction and an image, the model sees
    both alongside the current checklist, and can either answer in text or
    attach the image to an imageBlock via `add_image_to_block`.

    - `checklist` is the current JSON (the caller is responsible for snapshotting
      it into `checklist_prev` and persisting `result.checklist` afterwards).
    - `image_id` / `image_url` identify the already-uploaded file. The AI does
      NOT see these in its tool calls; the server injects them when applying
      `add_image_to_block`.
    - `image_data_url` is the base64-encoded `data:<mime>;base64,...` payload
      that goes into the chat completion's image content part.
    - `prior_messages` is the optional running chat history kept by the
      frontend so the user can ask follow-up questions about the same image.
    """
    result = AIRunResult(checklist=checklist)
    on_tool_call = _build_observe_callback(result, image_id, image_url, mode)

    system_prompt = build_observe_system_prompt(mode)
    user_text = (
        f"Current checklist JSON:\n```json\n{json.dumps(checklist, indent=2)}\n```\n\n"
        f"An image is attached to this message. (id={image_id})\n\n"
        f"User says: {instruction}"
    )

    client = OpenAIClient()
    chat_result = client.chat_with_tools_and_image(
        system_prompt,
        user_text,
        image_data_url,
        OBSERVE_TOOLS,
        on_tool_call,
        prior_messages=prior_messages,
        max_rounds=max_rounds,
    )
    result.reply = chat_result.reply

    return result


# Re-export helper so callers don't have to dig through tree_utils.
__all__ = [
    "AIRunResult",
    "edit_checklist_with_ai",
    "find_component_by_id",
    "generate_checklist_from_text",
    "observe_with_image",
    "review_checklist_with_ai",
]
