# AI Checklist Backend

This repository contains the proposed backend structure for an AI-assisted checklist web application.

The goal of the backend is to support:

- user registration and login
- JWT-based authentication
- checklist creation, reading, updating, and deletion
- checklist undo functionality
- AI-assisted checklist creation from natural language
- AI-assisted editing of existing checklists
- image uploads that can be referenced from checklist items

The backend is planned with **FastAPI** and follows a modular structure so that authentication, checklist logic, AI logic, image handling, and database access stay separated.

---

## Backend Structure

```txt
backend/
  app/
    main.py

    core/
      config.py

    db/
      session.py
      models.py

    auth/
      router.py
      service.py
      schemas.py

    checklists/
      router.py
      service.py
      schemas.py
      repository.py

    ai/
      router.py
      service.py
      schemas.py
      gemini_client.py
      prompts.py
      operations.py

    images/
      router.py
      service.py
      schemas.py
```

## Suggested responsibilities

```txt
main.py                  Creates the FastAPI app and includes routers.
core/config.py           Loads environment variables and global settings.
db/session.py            Creates DB engine, session factory, and get_db dependency.
db/models.py             Defines database tables.
auth/router.py           Auth HTTP endpoints.
auth/service.py          Auth logic: hashing, JWT, current user.
auth/schemas.py          Auth request/response schemas.
checklists/router.py     Checklist HTTP endpoints.
checklists/service.py    Checklist business logic, ownership checks, undo snapshots.
checklists/repository.py Checklist DB queries.
checklists/schemas.py    Checklist request/response schemas.
ai/router.py             AI HTTP endpoints.
ai/service.py            AI workflow orchestration.
ai/gemini_client.py      Wrapper around Gemini API.
ai/prompts.py            Prompt templates.
ai/operations.py         Applies AI-generated operations to checklist JSON.
images/router.py         Image upload endpoint.
images/service.py        Image storage logic.
images/schemas.py        Image response schemas.
```
## Suggested API endpoints

```txt
POST   /api/auth/register
POST   /api/auth/login
GET    /api/auth/me

GET    /api/checklists
POST   /api/checklists
GET    /api/checklists/{checklist_id}
PUT    /api/checklists/{checklist_id}
DELETE /api/checklists/{checklist_id}
POST   /api/checklists/{checklist_id}/undo

POST   /api/ai/checklists/{checklist_id}/edit
POST   /api/ai/checklists/create-from-text

POST   /api/images/upload
```

### Example

when the frontend sends a request to edit a checklist with AI, the flow should look like this:

```
frontend
  |
  v
ai/router.py
  |
  v
auth/service.py verifies the current user
  |
  v
ai/service.py loads the checklist and builds the prompt
  |
  v
ai/gemini_client.py calls the AI model
  |
  v
ai/operations.py applies the returned operations
  |
  v
checklists/service.py saves a snapshot and updates the checklist
  |
  v
updated checklist returned to frontend
```


# AI Checklist Backend Handoff

This archive contains:

- `openapi.yml`: OpenAPI 3.0 API specification for the proposed backend.
- `backend/app/`: suggested FastAPI backend file tree.
- Example Python files showing the intended responsibilities of each module.

The code is a scaffold / reference implementation, not a fully production-ready backend.
It is meant to help the team understand the architecture and start implementation.

---

## Implementation status

### Implemented: `app/services/checklist_update/`

The module that mutates a checklist's JSON via three operation types:
`addComponent`, `updateComponent`, `deleteComponent`. Every operation is validated for
shape (required fields, type checks, parent–child rules) and structural integrity
(target exists, component type matches the handler). All errors derive from
`ChecklistOperationError`.

**Supported component types** (see [`docs/component-structure.md`](../docs/component-structure.md)
for full field specs):
`section`, `checkboxGroup`, `checkbox`, `textField`, `numberField`, `imageBlock`, `table`.

**Single entry point**

```python
from app.services.checklist_update.service import apply_checklist_operations

updated_json = apply_checklist_operations(checklist_json, operations)
```

`operations` is a list of `AddComponentOperation` / `UpdateComponentOperation` /
`DeleteComponentOperation` objects (see `app/schemas/checklist_operations.py`).
Both manual frontend edits and AI tool calls converge on this function — there is
no separate "AI path" inside the mutation layer.

**How an HTTP route consumes the service** (see `app/api/routes/checklists.py::patch_checklist_route`):

1. Load the checklist for the current user.
2. Call `apply_checklist_operations(checklist.checklist, payload.operations)`.
3. Translate `ChecklistOperationError` subclasses to HTTP status codes:
   - `ComponentNotFoundError` → 404
   - `InvalidTargetContainerError`, `CannotDeleteRootError`,
     `UnsupportedOperationError`, `UnsupportedComponentTypeError`,
     `InvalidComponentPayloadError` → 400
4. On success, snapshot the previous JSON into `checklist_prev` (for undo),
   write the new JSON, commit, and return the row.

**Quick demo / smoke test**

```bash
cd backend
python test_add_delete_update.py
```

Runs 23 checks covering every component type's add/update/delete plus the
validation failure paths. Exits with status 0 if everything passes.

### Implemented: `app/services/ai/`

OpenAI-backed copilot that turns natural-language prompts into the same
`ChecklistOperation` list the manual edit flow accepts. The AI never writes to
the checklist JSON directly — it produces operations, the operations go through
`apply_checklist_operations`, and the same validators reject invalid model output.

**Entry points** (`app/services/ai/service.py`):

- `generate_checklist_from_text(prompt)` — builds a fresh checklist tree.
- `edit_checklist_with_ai(checklist, instruction)` — returns the modified checklist.

**Configuration**: set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`,
default `gpt-4o-mini`) in your environment or `.env`. Nothing else in the AI
module touches the DB or auth — it's a pure function over JSON.

**Routes** (`app/api/routes/ai.py`):

- `POST /api/ai/checklists/create-from-text`
- `POST /api/ai/checklists/{checklist_id}/edit`

**Standalone integration test**

```bash
cd backend
export OPENAI_API_KEY=sk-...
python test_ai_create_checklist.py
```

Sends one prompt to OpenAI and prints the generated checklist JSON.

