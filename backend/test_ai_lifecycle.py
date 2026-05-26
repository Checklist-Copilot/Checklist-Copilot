"""
End-to-end AI lifecycle smoke test: CREATE → EDIT on the same checklist.

Two phases in one run:

  Phase 1 — generate_checklist_from_text(...)
            Builds a fresh checklist from a natural-language description.

  Phase 2 — edit_checklist_with_ai(...)
            Edits the checklist produced in phase 1. The instruction is
            tolerant: it asks the model to pick targets it sees in the tree,
            so the test works regardless of which sections / fields phase 1
            produced. The instruction is crafted to require all three tool
            types: add_component, update_component, delete_component.

Neither phase needs a database. Both phases exercise the same validation
pipeline (`apply_checklist_operations`) that the manual edit route uses —
the AI is just another caller.

Run from `backend/`:

    $env:OPENAI_API_KEY = "sk-..."     # PowerShell
    python test_ai_lifecycle.py
    python test_ai_lifecycle.py "Pre-flight inspection checklist for a small drone"

For unit-level validator coverage (no AI, no key, no cost), see
`test_add_delete_update.py`.
"""
from __future__ import annotations

import json
import os
import sys

# Make `from app...` resolvable when running this file from backend/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai.service import (  # noqa: E402
    AIRunResult,
    edit_checklist_with_ai,
    generate_checklist_from_text,
)
from app.services.checklist_update.tree_utils import find_component_by_id  # noqa: E402


DEFAULT_CREATE_PROMPT = (
    "A daily pre-shift safety inspection checklist for a construction-site "
    "forklift operator. It should record the operator's name, the location "
    "code, ambient temperature, a PPE checklist (hard hat, vest, boots), and "
    "a small equipment status log table."
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
    # Summary                                                                 #
    # ---------------------------------------------------------------------- #
    print("\n" + "=" * 72)
    print("Summary")
    print("=" * 72)
    print(f"  Phase 1 (create): {create_result.applied_calls} components added")
    print(
        f"  Phase 2 (edit):   "
        f"+{edit_counts['add_component']} added, "
        f"~{edit_counts['update_component']} updated, "
        f"-{edit_counts['delete_component']} deleted"
    )
    total_skipped = len(create_result.skipped_calls) + len(edit_result.skipped_calls)
    print(f"  Total skipped:    {total_skipped}")

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

    print("\nOK: full create → edit lifecycle completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
