"""
End-to-end smoke test for the AI checklist generator.

What it does:
  1. Reads OPENAI_API_KEY from the environment.
  2. Sends one natural-language prompt to ChatGPT.
  3. Parses the returned tool calls into ChecklistOperations.
  4. Runs them through the same validation pipeline as manual edits
     (`apply_checklist_operations`).
  5. Prints the resulting checklist JSON, plus a short report on which calls
     the model made and which (if any) were rejected by the validators.

Run from the `backend/` directory:

    set  OPENAI_API_KEY=sk-...        (Windows CMD)
    $env:OPENAI_API_KEY = "sk-..."     (PowerShell)
    export OPENAI_API_KEY=sk-...       (bash/zsh)

    python test_ai_create_checklist.py
    python test_ai_create_checklist.py "Build a forklift inspection checklist"

By default we use gpt-4o-mini (cheap + supports tool calling). Override with
the OPENAI_MODEL env var if you want to try gpt-3.5-turbo-1106 or similar.

This script intentionally does NOT hit the database or the FastAPI routes —
it exercises the AI service directly so you can verify the model integration
without standing up Postgres / Supabase / JWT auth first.
"""
from __future__ import annotations

import json
import os
import sys

# Make `from app...` resolvable when running this file from backend/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai.service import generate_checklist_from_text  # noqa: E402


DEFAULT_PROMPT = (
    "A daily pre-shift safety inspection checklist for a construction-site "
    "forklift operator. It should record the operator's name, the location "
    "code, ambient temperature, a PPE checklist (hard hat, vest, boots), and "
    "a small equipment status log table."
)


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "ERROR: OPENAI_API_KEY is not set.\n"
            "  Windows CMD:  set OPENAI_API_KEY=sk-...\n"
            "  PowerShell:   $env:OPENAI_API_KEY = 'sk-...'\n"
            "  bash/zsh:     export OPENAI_API_KEY=sk-...",
            file=sys.stderr,
        )
        return 2

    prompt = " ".join(sys.argv[1:]).strip() or DEFAULT_PROMPT
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    print("=" * 72)
    print(f"Model:  {model}")
    print(f"Prompt: {prompt}")
    print("=" * 72)
    print("\nCalling OpenAI...\n")

    result = generate_checklist_from_text(prompt)

    print(f"Tool calls returned by the model: {len(result.raw_tool_calls)}")
    print(f"Applied:                          {result.applied_calls}")
    print(f"Skipped (validation failures):    {len(result.skipped_calls)}")

    if result.skipped_calls:
        print("\nSkipped calls:")
        for s in result.skipped_calls:
            print(f"  - {s['reason']}")
            print(f"    call: {json.dumps(s['call'], indent=4)[:400]}")

    print("\n" + "=" * 72)
    print("Generated checklist:")
    print("=" * 72)
    print(json.dumps(result.checklist, indent=2, ensure_ascii=False))

    # Quick sanity checks so the script exits non-zero on obviously bad output.
    children = result.checklist.get("children", [])
    if not children:
        print("\nFAIL: model produced no top-level children.", file=sys.stderr)
        return 1
    if result.applied_calls == 0:
        print("\nFAIL: no tool calls were applied successfully.", file=sys.stderr)
        return 1

    print("\nOK: checklist generated with "
          f"{result.applied_calls} component(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
