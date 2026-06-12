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
from app.services.ai.prompts import (
    build_create_system_prompt,
    build_edit_system_prompt,
    build_observe_system_prompt,
)
from app.services.ai.tools import ALL_TOOLS, CREATE_TOOLS, OBSERVE_TOOLS
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
    pdf_context: str | None = None,
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
    context_prefix = (
        f"The following text was extracted from a reference PDF document.\n\n"
        f"STRICT RULES — you MUST follow these:\n"
        f"1. ONLY create checklist items, sections, and fields that are EXPLICITLY "
        f"mentioned in the PDF text below. Do NOT add anything from general knowledge "
        f"or common practice that is not stated in the PDF.\n"
        f"2. Every checkbox item must correspond to a specific requirement or step "
        f"listed in the PDF — use the PDF's exact wording as the label.\n"
        f"3. Every section must correspond to a heading or logical group FROM the PDF.\n"
        f"4. Where the PDF specifies concrete values (names, codes, units, thresholds, "
        f"dates), use those exact values as field labels, placeholders, or defaults.\n"
        f"5. Do NOT invent fields, items, or sections that are not in the PDF.\n"
        f"6. If the PDF says to collect a piece of data (e.g. 'record inspector name'), "
        f"create the appropriate input field for it.\n"
        f"7. If the PDF mentions uploading a photo, create an imageBlock.\n\n"
        f"PDF CONTENT:\n{pdf_context}\n\n---\n\n"
        if pdf_context
        else ""
    )
    user_prompt = (
        f"{context_prefix}"
        f"Build a checklist for:\n\n{prompt}\n\n"
        f"The root container id is `{root_id}`. Use it as `targetContainerId` "
        f"for the top-level sections, then fill every section with the "
        f"appropriate fields and checkbox items. Keep going until done."
    )

    client = OpenAIClient()
    chat_result = client.chat_with_tools(
        system_prompt,
        user_prompt,
        CREATE_TOOLS,
        on_tool_call,
        max_rounds=max_rounds,
    )
    result.reply = chat_result.reply

    return result


def extract_checklist_structure_from_pdf(pdf_text: str) -> dict:
    """
    Phase 1: AI reads the raw PDF text and returns a structured JSON describing
    sections and items. Supports combined text from multiple PDFs (separated by ---).
    """
    client = OpenAIClient()
    system = (
        "You are a document analyst. You will receive text extracted from one or more PDF documents. "
        "Multiple documents are separated by '---'. Extract all content as a single unified checklist definition.\n\n"
        "Return ONLY valid JSON with this shape:\n"
        "{\n"
        '  "sections": ["Section Name 1", ...],\n'
        '  "required_fields": ["exact label of item that is required", ...],\n'
        '  "items": [\n'
        '    {"label": "...", "section": "Section Name", '
        '"fieldType": "checkbox|textField|numberField|imageBlock", "required": false}\n'
        '  ]\n'
        "}\n\n"
        "SECTION RULES:\n"
        "- Derive sections from document headings or logical topic groups.\n"
        "- If multiple documents cover the same topic, merge into one section — do NOT create duplicate section names.\n"
        "- Ignore intro/purpose sections that contain no actionable items.\n\n"
        "ITEM RULES:\n"
        "- One item per requirement, data field, or action mentioned.\n"
        "- Use the document's exact wording for labels (trim trailing periods).\n"
        "- Do NOT add items not mentioned in the documents.\n"
        "- Do NOT omit items that are mentioned.\n\n"
        "FIELD TYPE RULES:\n"
        "- 'checkbox': yes/no verification steps ('verify that...', 'check that...', 'confirm...', 'inspect...').\n"
        "- 'textField': free-text input (name, date as text, comments, descriptions, corrective actions).\n"
        "- 'numberField': numeric values with units (temperature, count, weight, pressure).\n"
        "- 'imageBlock': when the document says to upload, attach, or photograph something.\n\n"
        "REQUIRED FIELD RULES — mark required=true when the document contains ANY of:\n"
        "- The word 'mandatory', 'required', 'must', 'shall', 'obligatory' near the item.\n"
        "- Phrases like 'every X must', 'all X must', 'is required to', 'failure to X'.\n"
        "- The item appears in a section explicitly titled 'Required ...' or 'Mandatory ...'.\n"
        "- The item is a data collection field that the document says must be recorded/filled.\n"
        "- Also list every required item's exact label in the top-level 'required_fields' array.\n"
        "- When in doubt, prefer required=true for safety/inspection items."
    )
    return client.complete_json(system, f"Document text:\n\n{pdf_text}")


def _add_section(result: AIRunResult, root_id: str, section_name: str) -> str:
    """Create a section in root and return its generated id."""
    op = AddComponentOperation.model_construct(
        operation="addComponent",
        targetContainerId=root_id,
        component={"type": "section", "label": section_name},
        position="end",
    )
    result.checklist = apply_checklist_operations(result.checklist, [op])
    result.applied_calls += 1
    for child in reversed(result.checklist["children"]):
        if child.get("type") == "section" and child.get("label") == section_name:
            return child["id"]
    raise RuntimeError(f"Section '{section_name}' was not found after creation")


def _add_checkbox_group(result: AIRunResult, section_id: str, label: str) -> str:
    """Create a checkboxGroup inside a section and return its generated id."""
    op = AddComponentOperation.model_construct(
        operation="addComponent",
        targetContainerId=section_id,
        component={"type": "checkboxGroup", "label": label},
        position="end",
    )
    result.checklist = apply_checklist_operations(result.checklist, [op])
    result.applied_calls += 1

    def _find_section(node: dict, sid: str) -> dict | None:
        if node.get("id") == sid:
            return node
        for child in node.get("children", []):
            found = _find_section(child, sid)
            if found:
                return found
        return None

    sec_node = _find_section(result.checklist, section_id)
    if sec_node:
        for child in reversed(sec_node.get("children", [])):
            if child.get("type") == "checkboxGroup" and child.get("label") == label:
                return child["id"]
    raise RuntimeError(f"checkboxGroup '{label}' was not found after creation in section {section_id}")


def _build_checklist_from_structure(
    structure: dict,
    *,
    title: str | None,
    description: str | None,
) -> AIRunResult:
    """
    Phase 2 (deterministic): build the checklist tree from the Phase-1 JSON.

    Hierarchy rules enforced here (not left to AI):
      root → section → checkboxGroup → checkbox
      root → section → textField / numberField / imageBlock

    Every component is always inside a section. checkboxes are always inside
    a checkboxGroup which is always inside a section.
    """
    sections: list[str] = structure.get("sections") or []
    items: list[dict] = structure.get("items") or []
    required_labels: set[str] = {
        lbl.rstrip(".").strip().lower()
        for lbl in (structure.get("required_fields") or [])
        if isinstance(lbl, str)
    }

    root_id = f"root_{uuid.uuid4().hex[:12]}"
    checklist: dict[str, Any] = {
        "id": root_id,
        "type": "checklist",
        "title": title,
        "description": description,
        "children": [],
    }
    result = AIRunResult(checklist=checklist)

    # ------------------------------------------------------------------ #
    # Step 1: create all sections from Phase-1 list                       #
    # ------------------------------------------------------------------ #
    section_ids: dict[str, str] = {}
    for section_name in sections:
        sid = _add_section(result, root_id, section_name)
        section_ids[section_name] = sid
        print(f"  [STEP 3] section \"{section_name}\" → {sid}")

    # Fallback section — created on demand if an item names an unknown section
    _fallback_section_id: str | None = None

    def _get_or_create_section(name: str) -> str:
        nonlocal _fallback_section_id
        if name in section_ids:
            return section_ids[name]
        # Unknown section name from Phase 1 — create it on the fly
        if name:
            sid = _add_section(result, root_id, name)
            section_ids[name] = sid
            print(f"  [STEP 3] section (on-demand) \"{name}\" → {sid}")
            return sid
        # Empty section name — use/create a generic fallback
        if _fallback_section_id is None:
            _fallback_section_id = _add_section(result, root_id, "General")
            section_ids["General"] = _fallback_section_id
            print(f"  [STEP 3] section (fallback) \"General\" → {_fallback_section_id}")
        return _fallback_section_id

    # ------------------------------------------------------------------ #
    # Step 2: add items                                                    #
    # One checkboxGroup per section, created lazily on first checkbox.    #
    # ------------------------------------------------------------------ #
    checkbox_group_ids: dict[str, str] = {}

    for item in items:
        label = (item.get("label") or "").rstrip(".").strip()
        if not label:
            continue
        field_type = item.get("fieldType", "checkbox")
        section_name = item.get("section", "")
        required = bool(item.get("required", False)) or label.lower() in required_labels
        section_id = _get_or_create_section(section_name)

        if field_type == "checkbox":
            # Rule: checkbox must be inside a checkboxGroup which must be inside a section
            if section_name not in checkbox_group_ids:
                group_label = f"{section_name} Items" if section_name else "Inspection Items"
                gid = _add_checkbox_group(result, section_id, group_label)
                checkbox_group_ids[section_name] = gid
                print(f"  [STEP 3] checkboxGroup \"{group_label}\" in \"{section_name}\" → {gid}")

            op = AddComponentOperation.model_construct(
                operation="addComponent",
                targetContainerId=checkbox_group_ids[section_name],
                component={"type": "checkbox", "label": label, "required": required},
                position="end",
            )

        elif field_type == "textField":
            op = AddComponentOperation.model_construct(
                operation="addComponent",
                targetContainerId=section_id,
                component={"type": "textField", "label": label, "required": required},
                position="end",
            )

        elif field_type == "numberField":
            op = AddComponentOperation.model_construct(
                operation="addComponent",
                targetContainerId=section_id,
                component={"type": "numberField", "label": label, "required": required},
                position="end",
            )

        elif field_type == "imageBlock":
            op = AddComponentOperation.model_construct(
                operation="addComponent",
                targetContainerId=section_id,
                component={"type": "imageBlock", "label": label, "allowUpload": True},
                position="end",
            )

        else:
            result.skipped_calls.append({"item": item, "reason": f"unknown fieldType {field_type!r}"})
            print(f"  [STEP 3] SKIP \"{label}\" — unknown fieldType {field_type!r}")
            continue

        result.checklist = apply_checklist_operations(result.checklist, [op])
        result.applied_calls += 1
        req_marker = " [REQUIRED]" if required else ""
        print(f"  [STEP 3] OK [{field_type}] \"{label}\"{req_marker}")

    print(f"\n[STEP 3 — PHASE 2] DONE — applied={result.applied_calls} skipped={len(result.skipped_calls)}")
    print(f"{'='*60}\n")
    return result


def generate_checklist_from_pdf(
    pdf_text: str,
    *,
    title: str | None = None,
    description: str | None = None,
) -> AIRunResult:
    """
    Two-phase PDF-to-checklist generation:
    Phase 1 — AI extracts structured JSON (sections + items) from the PDF text.
    Phase 2 — deterministic Python builds the checklist tree from that JSON.
    """
    print(f"\n[STEP 2 — PHASE 1] Sending PDF text to AI for structured extraction...")
    structure = extract_checklist_structure_from_pdf(pdf_text)

    sections: list[str] = structure.get("sections") or []
    items: list[dict] = structure.get("items") or []

    required_fields_raw: list[str] = structure.get("required_fields") or []
    print(f"[STEP 2 — PHASE 1] AI returned {len(sections)} section(s), {len(items)} item(s), {len(required_fields_raw)} required field(s)")
    print(f"[STEP 2 — PHASE 1] SECTIONS:")
    for i, s in enumerate(sections):
        print(f"  [{i+1}] {s}")
    print(f"[STEP 2 — PHASE 1] REQUIRED FIELDS (cross-check list):")
    for rf in required_fields_raw:
        print(f"  • {rf}")
    print(f"[STEP 2 — PHASE 1] ITEMS:")
    for i, item in enumerate(items):
        print(f"  [{i+1}] [{item.get('fieldType','?')}] \"{item.get('label','?')}\" → section=\"{item.get('section','?')}\" required={item.get('required',False)}")

    if not sections and not items:
        print("[STEP 2 — PHASE 1] Nothing extracted — falling back to text generation")
        return generate_checklist_from_text(
            description or title or "checklist",
            title=title,
            description=description,
        )

    print(f"\n[STEP 3 — PHASE 2] Building checklist deterministically from {len(items)} items...")
    return _build_checklist_from_structure(structure, title=title, description=description)


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
    standard = _build_callback(result)

    def on_tool_call(call: ToolCall) -> dict:
        if call.name != "add_image_to_block":
            return standard(call)

        result.raw_tool_calls.append({"name": call.name, "arguments": call.arguments})
        args = call.arguments
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
    on_tool_call = _build_observe_callback(result, image_id, image_url)

    system_prompt = build_observe_system_prompt()
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
]
