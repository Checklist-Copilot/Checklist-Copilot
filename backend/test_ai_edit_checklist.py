"""
End-to-end smoke test for the AI checklist EDIT flow.

The point of this script is to demonstrate that the edit pipeline does NOT need
a database to work. `edit_checklist_with_ai(checklist_dict, instruction)` is a
pure function: hand it any checklist JSON and an instruction in English, it
returns a new checklist JSON.

For a real product run you would:
  1. Load the checklist row by ID from Postgres
  2. Call this function on `row.checklist`
  3. Snapshot the old JSON into `row.checklist_prev` (for undo)
  4. Save the new JSON back
That wiring lives in `app/api/routes/ai.py`. This test skips it.

Run from the `backend/` directory:

    $env:OPENAI_API_KEY = "sk-..."     # PowerShell
    python test_ai_edit_checklist.py
    python test_ai_edit_checklist.py "Add a section for forklift maintenance"
"""
from __future__ import annotations

import json
import os
import sys

# Make `from app...` resolvable when running this file from backend/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai.service import edit_checklist_with_ai  # noqa: E402


# A small hand-crafted checklist we'll ask the model to edit. Every id here is
# stable so you can see the model reuse them in update/delete tool calls.
STARTING_CHECKLIST: dict = {
    "id": "root_demo_0001",
    "type": "checklist",
    "title": "Forklift pre-shift inspection",
    "description": None,
    "children": [
        {
            "id": "sec_operator_info",
            "humanReadableId": "section_operator_info",
            "type": "section",
            "label": "Operator Information",
            "collapsed": False,
            "children": [
                {
                    "id": "field_operator_name",
                    "humanReadableId": "field_operator_name",
                    "type": "textField",
                    "label": "Operator Name",
                    "value": "",
                    "placeholder": "Full name",
                    "required": True,
                    "multiline": False,
                },
            ],
        },
        {
            "id": "sec_ppe",
            "humanReadableId": "section_ppe",
            "type": "section",
            "label": "PPE Checklist",
            "collapsed": False,
            "children": [
                {
                    "id": "group_ppe",
                    "humanReadableId": "group_ppe",
                    "type": "checkboxGroup",
                    "label": "Personal Protective Equipment",
                    "items": [
                        {
                            "id": "chk_hard_hat",
                            "type": "checkbox",
                            "label": "Hard hat is worn",
                            "checked": False,
                            "required": True,
                        },
                        {
                            "id": "chk_vest",
                            "type": "checkbox",
                            "label": "High-visibility vest is worn",
                            "checked": False,
                            "required": True,
                        },
                    ],
                },
            ],
        },
    ],
}


DEFAULT_INSTRUCTION = (
    "Add a new section called 'Environmental Conditions' that contains a "
    "numberField for ambient temperature in Celsius (min -20, max 60) and a "
    "textField for general site observations. Also add a 'Steel-toed boots are "
    "worn' checkbox to the existing PPE group."
)


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

    instruction = " ".join(sys.argv[1:]).strip() or DEFAULT_INSTRUCTION
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    print("=" * 72)
    print(f"Model:       {model}")
    print(f"Instruction: {instruction}")
    print("=" * 72)
    print("\nStarting checklist:")
    print(json.dumps(STARTING_CHECKLIST, indent=2))
    print("\nCalling OpenAI...\n")

    result = edit_checklist_with_ai(STARTING_CHECKLIST, instruction)

    print(f"Tool calls returned: {len(result.raw_tool_calls)}")
    print(f"Applied:             {result.applied_calls}")
    print(f"Skipped:             {len(result.skipped_calls)}")

    if result.skipped_calls:
        print("\nSkipped calls:")
        for s in result.skipped_calls:
            print(f"  - {s['reason']}")
            print(f"    call: {json.dumps(s['call'])[:300]}")

    print("\nTool calls made by the model:")
    for tc in result.raw_tool_calls:
        # Compact one-liner per call.
        args = json.dumps(tc["arguments"])
        if len(args) > 180:
            args = args[:177] + "..."
        print(f"  - {tc['name']}({args})")

    print("\n" + "=" * 72)
    print("Resulting checklist:")
    print("=" * 72)
    print(json.dumps(result.checklist, indent=2, ensure_ascii=False))

    # Sanity check: the model should have produced at least one applied call.
    if result.applied_calls == 0:
        print("\nFAIL: no tool calls were applied.", file=sys.stderr)
        return 1

    print(f"\nOK: edit applied {result.applied_calls} change(s) to the checklist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
