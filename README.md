# AI Checklist Copilot

A lightweight proof-of-concept checklist designer and execution environment with an AI copilot.

The goal is not to clone the full PAM LiveForms system, but to build a smaller demonstrator where users can create, edit, save, and use digital checklists. The key idea is that every checklist is represented internally as structured JSON, which can be rendered by the frontend and safely modified through validated AI tool calls.

## Core Idea

Users can design simple digital checklists containing elements such as sections, checkbox items, text fields, number fields, dropdowns, tables, images, and photo upload fields.

Instead of storing the checklist as raw HTML, the application stores it as a hierarchical JSON model. The frontend renders this JSON as an interactive checklist/form.

Each checklist element has:

- A globally unique technical `id`
- An optional human-readable `humanReadableId`
- A `type`
- A label and type-specific properties
- Optional child elements

This makes it possible to reliably update checklist elements even if their visible labels change.

## AI Copilot

The AI copilot modifies checklists through controlled tool calls instead of directly changing the UI or DOM.

Example user request:

```txt
Add a new safety section with three checkbox items.
```

The AI responds with structured actions such as:

```
{
  "tool": "add_element",
  "parentId": "018f6c4a-8a4e-7b91-bb2f-6d3c2f019284",
  "element": {
    "id": "018f6c4c-84e2-758a-8d9b-31f81e110aa2",
    "humanReadableId": "item_protective_equipment_worn",
    "type": "checkbox",
    "label": "Protective equipment is worn",
    "checked": false
  }
}
```

The application validates the action, applies it to the checklist JSON, and re-renders the UI.

## General Flow

```
User request
→ LLM interprets request
→ LLM returns structured tool call
→ App validates the action
→ App stores the previous checklist snapshot
→ App updates checklist JSON
→ Frontend re-renders checklist
```

Before applying an AI-generated change, the backend stores the previous checklist state as a snapshot. If the user wants to revert the last change, the frontend can call the undo API, which restores the previous snapshot.

## Manual Editing Flow

When the user edits the checklist manually in the frontend, the checklist JSON is still the source of truth.

For example, if the user changes a field label, checks an item, adds a new element, or deletes a section, the frontend first updates the local checklist JSON state. After that, the updated JSON is sent to the backend so the new version can be saved in the database.

```txt
User manually edits checklist
→ Frontend updates local checklist JSON
→ Frontend re-renders checklist from updated JSON
→ Frontend sends updated JSON to backend
→ Backend validates and saves new version in database
```
