"""
End-to-end AI lifecycle smoke test: CREATE → EDIT → OBSERVE.

Three phases in one run:

  Phase 1 — generate_checklist_from_text(...)
            Builds a fresh checklist from a natural-language description.

  Phase 2 — edit_checklist_with_ai(...)
            Edits the checklist produced in phase 1. The instruction is
            tolerant: it asks the model to pick targets it sees in the tree,
            so the test works regardless of which sections / fields phase 1
            produced. The instruction is crafted to require all three tool
            types: add_component, update_component, delete_component.

  Phase 3 — observe_with_image(...)
            Vision flow. Uses a hand-crafted checklist with several distinct
            imageBlocks (PPE, Engine, Site Conditions) and the local image
            `car-engine-compressed.jpg`. Verifies the AI either describes the
            image in text OR attaches it to the engine-related imageBlock —
            proving it can map an image to the right place in the checklist.

None of these phases need a database. Every phase exercises the same
validation pipeline (`apply_checklist_operations`) that the manual edit route
uses — the AI is just another caller.

Run from `backend/`:

    $env:OPENAI_API_KEY = "sk-..."     # PowerShell
    python test_ai_lifecycle.py
    python test_ai_lifecycle.py "Pre-flight inspection checklist for a small drone"

For unit-level validator coverage (no AI, no key, no cost), see
`test_add_delete_update.py`.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys

# Make `from app...` resolvable when running this file from backend/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai.service import (  # noqa: E402
    AIRunResult,
    edit_checklist_with_ai,
    generate_checklist_from_text,
    observe_with_image,
)
from app.services.checklist_update.tree_utils import find_component_by_id  # noqa: E402


# Path to the local test image (committed to the repo for offline runs).
_IMAGE_FILENAME = "car-engine-compressed.jpg"
_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), _IMAGE_FILENAME)


# Helpers used by Phase 3 to inspect imageBlocks in the lifecycle's checklist
# and to confirm where the AI ended up attaching the image.

def _collect_image_blocks(node: Any, acc: list[dict] | None = None) -> list[dict]:
    """Return every imageBlock found anywhere in the tree."""
    if acc is None:
        acc = []
    if isinstance(node, dict):
        if node.get("type") == "imageBlock":
            acc.append(node)
        for key in ("children", "items"):
            for child in node.get(key, []) or []:
                _collect_image_blocks(child, acc)
    return acc


def _find_block_containing_image(node: Any, image_id: str) -> dict | None:
    """Locate the imageBlock whose `images` array contains the given imageId."""
    if isinstance(node, dict):
        if node.get("type") == "imageBlock":
            for img in node.get("images", []) or []:
                if isinstance(img, dict) and img.get("imageId") == image_id:
                    return node
        for key in ("children", "items"):
            for child in node.get(key, []) or []:
                found = _find_block_containing_image(child, image_id)
                if found is not None:
                    return found
    return None


DEFAULT_CREATE_PROMPT = (
    "A daily pre-shift safety inspection checklist for a construction-site "
    "forklift operator. It should record the operator's name, the location "
    "code, ambient temperature, a PPE checklist (hard hat, vest, boots), "
    "a small equipment status log table, AND an imageBlock under an engine / "
    "forklift inspection section where the operator can attach photos of the "
    "forklift engine or any visible damage. The imageBlock should have a clear "
    "label like 'Engine Inspection Photos' so the AI can find it later."
)

# A realistic edit instruction phrased the way a forklift operator might
# actually type it after their pre-shift check. It assumes the create prompt
# above produced the usual structure (operator info, environmental conditions,
# PPE checkboxes for hard hat / vest / boots, equipment status table) — if the
# model deviates and skips some changes, that's fine; the test reports what
# was applied either way.
DEFAULT_EDIT_INSTRUCTION = (
    "Quick update from my pre-shift inspection: my name is John Doe, I'm at "
    "site L-12, and the temperature this morning is 18 °C. Hard hat and boots "
    "are on. I forgot my safety vest today, so please remove the vest line "
    "from the checklist. Also add a new 'Forklift horn tested' checkbox "
    "to the list since we just realised we need to track that."
)


def _find_by_human_readable_id(node: dict, hrid: str) -> dict | None:
    """Mirror of the lookup the AI service does, so we can resolve parent refs."""
    if node.get("humanReadableId") == hrid:
        return node
    for key in ("children", "items"):
        for child in node.get(key, []) or []:
            if isinstance(child, dict):
                found = _find_by_human_readable_id(child, hrid)
                if found is not None:
                    return found
    return None


def _describe_applied_changes(
    pre_checklist: dict,
    post_checklist: dict,
    raw_tool_calls: list[dict],
    skipped_calls: list[dict],
) -> list[str]:
    """
    Walk the raw tool calls in order, filtering out the ones that were skipped,
    and return one human-readable line per APPLIED call.

    For updates/deletes we look up the target's label in the pre-edit checklist
    (that's what the model intended to act on). For adds we use the new label
    from the call args and look up the parent in the post-edit checklist
    (since the parent may have been added earlier in the same phase).
    """
    lines: list[str] = []

    # skipped_calls preserves the order in which calls failed, so we can walk
    # raw_tool_calls + skipped_calls together to identify which ones applied.
    skipped_iter = iter(skipped_calls)
    next_skipped = next(skipped_iter, None)

    for raw in raw_tool_calls:
        if next_skipped is not None and next_skipped["call"] == raw:
            next_skipped = next(skipped_iter, None)
            continue  # this call was rejected; not part of "what changed"

        name = raw["name"]
        args = raw.get("arguments", {})

        if name == "add_component":
            comp = args.get("component", {}) or {}
            ctype = comp.get("type", "?")
            label = comp.get("label", "?")
            target_ref = args.get("targetContainerId", "?")
            # Parent might be a real id or a humanReadableId — try both against
            # the post-edit checklist (the parent may have been added in-phase).
            parent = (
                find_component_by_id(post_checklist, target_ref)
                or _find_by_human_readable_id(post_checklist, target_ref)
            )
            parent_label = parent.get("label", target_ref) if parent else target_ref
            lines.append(f"[add]    {ctype:13s} {label!r}  ->  parent={parent_label!r}")

        elif name == "update_component":
            target_id = args.get("targetId", "?")
            patch = args.get("patch", {}) or {}
            target = (
                find_component_by_id(pre_checklist, target_id)
                or find_component_by_id(post_checklist, target_id)
            )
            if target is not None:
                ctype = target.get("type", "?")
                label = target.get("label", "?")
                lines.append(
                    f"[update] {ctype:13s} {label!r}  ({target_id})  patch={json.dumps(patch, ensure_ascii=False)}"
                )
            else:
                lines.append(
                    f"[update] {'?':13s} (id={target_id})  patch={json.dumps(patch, ensure_ascii=False)}"
                )

        elif name == "delete_component":
            target_id = args.get("targetId", "?")
            target = find_component_by_id(pre_checklist, target_id)
            if target is not None:
                ctype = target.get("type", "?")
                label = target.get("label", "?")
                lines.append(f"[delete] {ctype:13s} {label!r}  ({target_id})")
            else:
                lines.append(f"[delete] {'?':13s} (id={target_id})")

    return lines


def _print_result(label: str, result: AIRunResult) -> dict[str, int]:
    """
    Pretty-print the outcome of one AI phase and return a per-tool applied count.
    """
    applied_by_type: dict[str, int] = {
        "add_component": 0,
        "update_component": 0,
        "delete_component": 0,
    }
    # raw_tool_calls includes successes AND failures; subtract the failures.
    for tc in result.raw_tool_calls:
        name = tc.get("name")
        if name in applied_by_type:
            applied_by_type[name] += 1
    for s in result.skipped_calls:
        name = s["call"].get("name")
        if name in applied_by_type:
            applied_by_type[name] = max(0, applied_by_type[name] - 1)

    print(f"--- {label} ---")
    print(f"Tool calls returned: {len(result.raw_tool_calls)}")
    print(f"Applied:             {result.applied_calls}")
    print(f"Skipped:             {len(result.skipped_calls)}")
    print("By tool (applied):")
    for name, count in applied_by_type.items():
        marker = "OK " if count > 0 else "-- "
        print(f"  {marker}{name}: {count}")

    if result.skipped_calls:
        print("Skipped calls:")
        for s in result.skipped_calls:
            print(f"  - {s['reason']}")

    # The model's natural-language reply (its "speech" channel) — this is what
    # the frontend shows the user in the chat panel.
    print(f'AI reply: {result.reply or "(none)"}')

    return applied_by_type


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "ERROR: OPENAI_API_KEY is not set.\n"
            "  PowerShell:   $env:OPENAI_API_KEY = 'sk-...'\n"
            "  CMD:          set OPENAI_API_KEY=sk-...\n"
            "  bash/zsh:     export OPENAI_API_KEY=sk-...",
            file=sys.stderr,
        )
        return 2

    create_prompt = " ".join(sys.argv[1:]).strip() or DEFAULT_CREATE_PROMPT
    edit_instruction = DEFAULT_EDIT_INSTRUCTION
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    print("=" * 72)
    print(f"Model: {model}")
    print()
    print("Create prompt:")
    for line in create_prompt.splitlines() or [create_prompt]:
        print(f"  {line}")
    print()
    print("Edit instruction:")
    for line in edit_instruction.splitlines():
        print(f"  {line}")
    print("=" * 72)

    # ---------------------------------------------------------------------- #
    # PHASE 1 — CREATE                                                        #
    # ---------------------------------------------------------------------- #
    print("\n[PHASE 1] Calling OpenAI to generate a checklist...\n")
    create_result = generate_checklist_from_text(create_prompt)
    create_counts = _print_result("phase 1: create", create_result)

    print("\nGenerated checklist:")
    print(json.dumps(create_result.checklist, indent=2, ensure_ascii=False))

    if create_result.applied_calls == 0:
        print("\nFAIL: phase 1 produced no applied tool calls.", file=sys.stderr)
        return 1
    if not create_result.checklist.get("children"):
        print("\nFAIL: phase 1 produced no top-level components.", file=sys.stderr)
        return 1

    # ---------------------------------------------------------------------- #
    # PHASE 2 — EDIT (feeds phase 1's output back in)                         #
    # ---------------------------------------------------------------------- #
    print("\n" + "=" * 72)
    print("[PHASE 2] Editing the generated checklist with a follow-up instruction...\n")
    # Keep a deep copy of the pre-edit tree so the diff below can look up
    # labels of components that get deleted or patched in this phase.
    import copy
    pre_edit_checklist = copy.deepcopy(create_result.checklist)

    edit_result = edit_checklist_with_ai(create_result.checklist, edit_instruction)
    edit_counts = _print_result("phase 2: edit", edit_result)

    # Human-readable "what changed" log — lets you confirm each item in the
    # final JSON below corresponds to an applied tool call.
    changes = _describe_applied_changes(
        pre_edit_checklist,
        edit_result.checklist,
        edit_result.raw_tool_calls,
        edit_result.skipped_calls,
    )
    print("\nApplied changes (in order):")
    if changes:
        for line in changes:
            print(f"  {line}")
    else:
        print("  (none — all tool calls were skipped or none were made)")

    print("\nChecklist after edit:")
    print(json.dumps(edit_result.checklist, indent=2, ensure_ascii=False))

    if edit_result.applied_calls == 0:
        print("\nFAIL: phase 2 produced no applied tool calls.", file=sys.stderr)
        return 1

    # ---------------------------------------------------------------------- #
    # PHASE 3 — OBSERVE (vision) on the SAME checklist from phases 1 & 2     #
    # ---------------------------------------------------------------------- #
    print("\n" + "=" * 72)
    print(f"[PHASE 3] Vision: sending '{_IMAGE_FILENAME}' to the AI against")
    print("          the checklist built in phase 1 and edited in phase 2.")
    print("          The AI should attach the image to whichever imageBlock")
    print("          best matches an engine photo.\n")

    phase3_attached_block: dict | None = None
    phase3_skipped = False
    phase3_checklist = edit_result.checklist  # default: the lifecycle's checklist
    fake_image_id = "test-image-car-engine"

    if not os.path.exists(_IMAGE_PATH):
        print(
            f"  SKIP: {_IMAGE_PATH} not found — skipping phase 3.",
            file=sys.stderr,
        )
        phase3_skipped = True
    else:
        # Are there any imageBlocks in the lifecycle's checklist for the AI to
        # attach to? Print them so we can see what phase 1 produced.
        blocks_before = _collect_image_blocks(phase3_checklist)
        print(f"imageBlocks present before observe: {len(blocks_before)}")
        for blk in blocks_before:
            print(f"  - {blk.get('label')!r} (id={blk.get('id')})")

        if not blocks_before:
            print(
                "\n  WARN: no imageBlocks in the lifecycle's checklist — the AI",
                "\n        has nowhere to attach the image. Skipping attach.",
                file=sys.stderr,
            )
        else:
            with open(_IMAGE_PATH, "rb") as fh:
                image_bytes = fh.read()
            mime, _ = mimetypes.guess_type(_IMAGE_PATH)
            mime = mime or "image/jpeg"
            image_data_url = (
                f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
            )

            # Fake id + URL — this test doesn't hit Supabase. The same strings
            # are what the AI will write into the imageBlock's images[] entry,
            # so we can recognise our image afterwards.
            fake_image_url = f"/api/files/{fake_image_id}/raw"

            observe_instruction = (
                "I just took this photo during my pre-shift inspection. Please "
                "look at it, briefly tell me what you see, AND add it to the "
                "imageBlock in this checklist where it best belongs. If no block "
                "is a good match, say so and don't attach."
            )

            print("\nCalling OpenAI (vision)...\n")
            observe_result = observe_with_image(
                phase3_checklist,
                observe_instruction,
                image_id=fake_image_id,
                image_url=fake_image_url,
                image_data_url=image_data_url,
                max_rounds=3,
            )

            print(f"Tool calls returned: {len(observe_result.raw_tool_calls)}")
            print(f"Applied:             {observe_result.applied_calls}")
            print(f"Skipped:             {len(observe_result.skipped_calls)}")
            if observe_result.skipped_calls:
                print("Skipped calls:")
                for s in observe_result.skipped_calls:
                    print(f"  - {s['reason']}")
            print(f"AI reply: {observe_result.reply or '(none)'}")

            # The lifecycle checklist now reflects whatever the AI did.
            phase3_checklist = observe_result.checklist
            phase3_attached_block = _find_block_containing_image(
                phase3_checklist, fake_image_id
            )

            if phase3_attached_block is not None:
                print(
                    f"\nImage landed in: "
                    f"{phase3_attached_block.get('label')!r} "
                    f"(id={phase3_attached_block.get('id')})"
                )
                print("This imageBlock now contains:")
                print(json.dumps(phase3_attached_block, indent=2, ensure_ascii=False))
            else:
                print(
                    "\n  AI did NOT attach the image — reply only. The "
                    "checklist is unchanged in phase 3."
                )

    # Always print the final lifecycle checklist (after all three phases) so
    # you can confirm visually where the image ended up.
    print("\n" + "=" * 72)
    print("Final lifecycle checklist (after phase 3):")
    print("=" * 72)
    print(json.dumps(phase3_checklist, indent=2, ensure_ascii=False))

    # ---------------------------------------------------------------------- #
    # Summary                                                                 #
    # ---------------------------------------------------------------------- #
    print("\n" + "=" * 72)
    print("Summary")
    print("=" * 72)
    print(f"  Phase 1 (create):  {create_result.applied_calls} components added")
    print(
        f"  Phase 2 (edit):    "
        f"+{edit_counts['add_component']} added, "
        f"~{edit_counts['update_component']} updated, "
        f"-{edit_counts['delete_component']} deleted"
    )
    if phase3_skipped:
        print("  Phase 3 (observe): SKIPPED (image file missing)")
    elif phase3_attached_block is not None:
        print(
            f"  Phase 3 (observe): image attached to "
            f"{phase3_attached_block.get('label')!r}"
        )
    else:
        print("  Phase 3 (observe): text-only reply, no attachment")

    total_skipped = len(create_result.skipped_calls) + len(edit_result.skipped_calls)
    print(f"  Total skipped:     {total_skipped}")

    # Soft warning when the default edit instruction was used but the model
    # didn't reach for all three op types. Not a hard fail — the model may have
    # legitimately found nothing to delete, etc.
    if not sys.argv[1:]:
        missing = [n for n, c in edit_counts.items() if c == 0]
        if missing:
            print(
                f"\nWARN: default edit instruction expected all 3 op types, "
                f"but these were not used in phase 2: {missing}",
                file=sys.stderr,
            )

    print("\nOK: full create → edit → observe lifecycle completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
