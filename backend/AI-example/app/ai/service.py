import json

from sqlalchemy.orm import Session

from app.ai.gemini_client import GeminiClient
from app.ai.operations import apply_operations
from app.ai.prompts import EDIT_CHECKLIST_PROMPT, CREATE_CHECKLIST_FROM_TEXT_PROMPT
from app.checklists.service import (
    get_user_checklist,
    update_user_checklist,
    create_user_checklist,
)


def edit_checklist_with_ai(
    db: Session,
    checklist_id: int,
    user_id: int,
    instruction: str,
):
    checklist = get_user_checklist(db, checklist_id, user_id)

    prompt = f"""
{EDIT_CHECKLIST_PROMPT}

Current checklist JSON:
{json.dumps(checklist.data, indent=2)}

User instruction:
{instruction}
"""

    gemini = GeminiClient()
    result = gemini.generate_json(prompt)

    operations = result.get("operations", [])
    updated_data = apply_operations(checklist.data, operations)

    updated_checklist = update_user_checklist(
        db,
        checklist_id=checklist.id,
        user_id=user_id,
        title=None,
        data=updated_data,
    )

    return {
        "operations": operations,
        "checklist": updated_checklist.data,
        "explanation": result.get("explanation"),
    }


def create_checklist_from_text(
    db: Session,
    user_id: int,
    text: str,
):
    prompt = f"""
{CREATE_CHECKLIST_FROM_TEXT_PROMPT}

User text:
{text}
"""

    gemini = GeminiClient()
    result = gemini.generate_json(prompt)

    title = result.get("title", "Untitled checklist")

    return create_user_checklist(
        db,
        user_id=user_id,
        title=title,
        data=result,
    )
