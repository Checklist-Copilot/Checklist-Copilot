# AI Checklist Copilot — Frontend, Backend, JSON Model, GenAI Tool Calls, Database and Storage Architecture

## 1. Purpose of this document

This document explains the planned architecture of the **AI Checklist Copilot** web application.

The goal of the project is to build a proof-of-concept web application where users can:

- create digital checklists;
- edit checklist structure manually in the frontend;
- use a checklist in execution mode;
- save checklist data in a backend/database;
- upload images and PDFs connected to a checklist;
- ask a GenAI assistant to create or edit checklist content;
- let the AI modify the checklist only through controlled, validated operations instead of directly rewriting the whole checklist JSON.

This document is written for a team where not everyone is familiar with **React**, **FastAPI**, REST APIs, JSONB databases, or structured GenAI tool calls. For that reason, it also explains basic concepts such as:

- what a React component is;
- what an endpoint is;
- what request/response means;
- how frontend and backend communicate;
- why the checklist is represented as JSON;
- how database tables and storage buckets fit into the system.

---

## 2. High-level project idea

The application is not meant to clone a full industrial checklist product. It is a smaller demonstrator showing how a checklist can be represented as a structured JSON object and safely modified by both humans and AI.

The central idea is:

> A checklist is stored as structured JSON, rendered by the frontend, validated by the backend, and edited by the AI through explicit tool-call operations.

Instead of storing the checklist as raw HTML, Markdown, or a PDF, the checklist is stored as a tree of structured objects. For example, a checklist can contain sections, checkbox groups, text fields, number fields, tables, image sections, and PDF references.

This has several advantages:

- the frontend can render the checklist dynamically;
- the backend can validate the checklist structure;
- the database can store the checklist as JSONB;
- the AI can safely refer to specific checklist elements by ID;
- updates can be applied to individual components instead of replacing the whole checklist;
- undo/history features become easier because changes can be represented as operations or snapshots.

---

## 3. Overall system architecture

The system can be thought of as four main parts:

```text
User Browser
   |
   | HTTP requests / JSON responses
   v
Frontend React App
   |
   | API calls
   v
FastAPI Backend
   |
   | SQL queries / object storage operations / GenAI calls
   v
Database + Storage + GenAI API
```

The frontend is responsible for the user interface. It displays checklist pages, edit mode, use mode, forms, buttons, tables, image upload controls, and the AI chat/edit interface.

The backend is responsible for business logic. It receives API requests from the frontend, validates them, talks to the database, calls the GenAI service, applies AI operations to the checklist JSON, and returns updated data.

The database stores users, checklist metadata, checklist JSON documents, and references to uploaded files.

The storage service stores actual binary files such as images and PDFs. The database should not normally store image or PDF bytes directly. It should store paths/references to files in storage buckets.

The GenAI API receives a user instruction plus the relevant checklist context and returns structured output. That structured output is not free-form text only. It should contain a specific operation/tool call such as `addComponent`, `updateComponent`, `deleteComponent`, or `reorderComponent`.

---

## 4. Important beginner concepts

### 4.1 What is the frontend?

The frontend is the part of the application that runs in the user's browser.

In this project, the frontend will likely be built with **React** and TypeScript. React is a JavaScript library for building user interfaces.

The frontend is responsible for things like:

- showing the list of checklists;
- showing a checklist editor;
- showing a checklist use/execution view;
- rendering JSON components as visible UI elements;
- letting the user type into fields;
- letting the user check checkboxes;
- letting the user upload images/PDFs;
- sending API requests to the backend;
- displaying responses from the backend;
- showing AI suggestions or applied AI changes.

The frontend should not directly talk to the database. It should talk to the backend through API calls.

---

### 4.2 What is the backend?

The backend is the server-side part of the application.

In this project, the backend is planned with **FastAPI**, a Python framework for building APIs.

The backend is responsible for:

- authentication and user management;
- receiving checklist API requests;
- validating request data;
- reading and writing checklist data in the database;
- generating upload paths for files;
- saving metadata for uploaded images/PDFs;
- calling the GenAI API;
- validating the AI's structured output;
- applying AI tool-call operations to the checklist JSON;
- returning clean JSON responses to the frontend.

The backend acts as the trusted middle layer between the frontend, the database, storage, and the GenAI API.

---

### 4.3 What is an API?

An API is a defined way for two pieces of software to communicate.

In this project, the frontend communicates with the backend through a web API.

For example, when the frontend wants to load a checklist, it sends a request like:

```http
GET /api/checklists/123
```

The backend receives this request, fetches checklist `123` from the database, and returns JSON:

```json
{
  "id": "123",
  "title": "Machine Inspection Checklist",
  "content": {
    "id": "root",
    "type": "root",
    "version": 1,
    "children": []
  }
}
```

---

### 4.4 What is an endpoint?

An endpoint is one specific URL plus HTTP method exposed by the backend.

Examples:

```text
GET    /api/checklists
POST   /api/checklists
GET    /api/checklists/{checklist_id}
PUT    /api/checklists/{checklist_id}
DELETE /api/checklists/{checklist_id}
```

Each endpoint has a specific purpose.

For example:

- `GET /api/checklists` returns all checklists for the current user.
- `POST /api/checklists` creates a new checklist.
- `GET /api/checklists/{checklist_id}` loads one checklist.
- `PUT /api/checklists/{checklist_id}` saves changes to one checklist.
- `DELETE /api/checklists/{checklist_id}` deletes one checklist.

The frontend does not call Python functions directly. It sends HTTP requests to these endpoints.

---

### 4.5 What is a React component?

A React component is a reusable piece of user interface.

For example, a checklist page could be built from components like this:

```text
ChecklistPage
├── ChecklistHeader
├── SectionRenderer
│   ├── CheckboxGroupRenderer
│   ├── TextFieldRenderer
│   ├── NumberFieldRenderer
│   ├── TableRenderer
│   └── ImageSectionRenderer
└── AiAssistantPanel
```

Each component receives data and decides how to display it.

A simple React component could look like this:

```tsx
function TextFieldRenderer({ component }) {
  return (
    <label>
      {component.label}
      <input value={component.value} />
    </label>
  );
}
```

In this project, the most important frontend idea is that React components will render checklist JSON objects based on their `type` field.

For example:

```tsx
function ComponentRenderer({ component }) {
  switch (component.type) {
    case "checkboxGroup":
      return <CheckboxGroupRenderer component={component} />;
    case "textField":
      return <TextFieldRenderer component={component} />;
    case "numberField":
      return <NumberFieldRenderer component={component} />;
    case "table":
      return <TableRenderer component={component} />;
    case "imageSection":
      return <ImageSectionRenderer component={component} />;
    default:
      return null;
  }
}
```

This means the frontend does not need a hardcoded checklist page for every checklist. It receives JSON and renders the UI dynamically.

---

## 5. Checklist JSON design

### 5.1 Why use JSON?

JSON is a structured data format. It is easy to send over HTTP, easy to store in a database, and easy to use in JavaScript/TypeScript and Python.

The checklist is not stored as plain text. It is stored as a tree of objects.

A simplified checklist could look like this:

```json
{
  "id": "root",
  "type": "root",
  "version": 1,
  "children": [
    {
      "id": "section_general",
      "type": "section",
      "title": "General Information",
      "children": [
        {
          "id": "field_operator_name",
          "type": "textField",
          "label": "Operator name",
          "value": ""
        }
      ]
    }
  ]
}
```

The main principle is:

> Every checklist object has an `id` and a `type`.

The `id` is used to identify a specific object.

The `type` tells the frontend and backend what kind of object it is.

---

### 5.2 Checklist as a tree

The checklist should be understood as a tree:

```text
Root
└── Section
    ├── Checkbox Container
    │   ├── Checkbox Item
    │   └── Checkbox Item
    ├── Text Field
    ├── Numeric Field
    ├── Table
    └── Images Section
```

Some objects are containers. They contain other objects.

Examples of container objects:

- `root`
- `section`
- `checkboxContainer`
- `imagesSection`

Some objects are leaf components. They do not contain children.

Examples of leaf objects:

- `checkboxItem`
- `textField`
- `numericField`
- a single uploaded image reference
- a PDF reference

---

### 5.3 Root object

The root object is the top-level checklist document.

Recommended structure:

```json
{
  "id": "root",
  "type": "root",
  "version": 1,
  "title": "Machine Inspection Checklist",
  "children": []
}
```

Fields:

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable ID of the root object. Can simply be `root`. |
| `type` | string | Always `root`. |
| `version` | number | Version of the checklist JSON schema. |
| `title` | string | Human-readable checklist title. |
| `children` | array | List of top-level checklist sections/components. |

Earlier we discussed using a default value similar to:

```json
{
  "id": "0",
  "type": "root",
  "version": "1",
  "children": []
}
```

A slightly improved version would use `root` as ID and store `version` as a number:

```json
{
  "id": "root",
  "type": "root",
  "version": 1,
  "children": []
}
```

Using a number for `version` makes later migrations easier.

---

### 5.4 Section object

A section groups related checklist components.

Example:

```json
{
  "id": "section_general_info",
  "type": "section",
  "title": "General Information",
  "description": "Basic information about this inspection.",
  "children": []
}
```

Fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Unique ID of the section. |
| `type` | string | yes | Always `section`. |
| `title` | string | yes | Section title shown to the user. |
| `description` | string | no | Optional explanatory text. |
| `children` | array | yes | Components inside the section. |

Sections are important because most AI operations will target sections. For example:

```json
{
  "operation": "addComponent",
  "targetContainerId": "section_general_info",
  "component": {
    "id": "text_operator_name",
    "type": "textField",
    "label": "Operator name",
    "value": ""
  }
}
```

---

### 5.5 Checkbox container object

A checkbox container groups multiple checkbox items.

Example:

```json
{
  "id": "checkbox_container_safety",
  "type": "checkboxContainer",
  "title": "Safety Checks",
  "items": [
    {
      "id": "checkbox_emergency_stop",
      "type": "checkboxItem",
      "label": "Emergency stop button works",
      "checked": false
    },
    {
      "id": "checkbox_guard_installed",
      "type": "checkboxItem",
      "label": "Protective guard is installed",
      "checked": false
    }
  ]
}
```

Fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Unique ID of the checkbox container. |
| `type` | string | yes | Always `checkboxContainer`. |
| `title` | string | yes | Title shown above the checkbox list. |
| `items` | array | yes | List of checkbox items. |

A checkbox container should use `items`, not `children`, because it is a specialized component. The contained objects are specifically checkbox items.

---

### 5.6 Checkbox item object

A checkbox item represents one checkable task.

Example:

```json
{
  "id": "checkbox_emergency_stop",
  "type": "checkboxItem",
  "label": "Emergency stop button works",
  "checked": false,
  "required": true
}
```

Fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Unique ID of the checkbox item. |
| `type` | string | yes | Always `checkboxItem`. |
| `label` | string | yes | Text shown next to the checkbox. |
| `checked` | boolean | yes | Whether the item is currently checked. |
| `required` | boolean | no | Whether this item must be checked before completion. |

For a template checklist, `checked` should usually start as `false`.

For a filled-out checklist execution, `checked` represents the user's actual answer.

---

### 5.7 Text field object

A text field allows the user to enter free-form text.

Example:

```json
{
  "id": "text_operator_name",
  "type": "textField",
  "label": "Operator name",
  "placeholder": "Enter operator name",
  "value": "",
  "required": true
}
```

Fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Unique ID of the text field. |
| `type` | string | yes | Always `textField`. |
| `label` | string | yes | Field label shown to the user. |
| `placeholder` | string | no | Placeholder text in the input. |
| `value` | string | yes | Current value of the field. |
| `required` | boolean | no | Whether this field must be filled. |

---

### 5.8 Numeric field object

A numeric field allows the user to enter a number.

Example:

```json
{
  "id": "number_temperature",
  "type": "numericField",
  "label": "Temperature",
  "value": null,
  "unit": "°C",
  "min": 0,
  "max": 100,
  "required": false
}
```

Fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Unique ID of the numeric field. |
| `type` | string | yes | Always `numericField`. |
| `label` | string | yes | Field label shown to the user. |
| `value` | number or null | yes | Current numeric value. |
| `unit` | string | no | Unit displayed next to the field. |
| `min` | number | no | Optional minimum allowed value. |
| `max` | number | no | Optional maximum allowed value. |
| `required` | boolean | no | Whether this field must be filled. |

Using `null` for an empty numeric field is better than using an empty string because it clearly means “no number entered yet.”

---

### 5.9 Table object

A table stores structured rows and columns.

Example:

```json
{
  "id": "table_measurements",
  "type": "table",
  "title": "Measurements",
  "columns": [
    {
      "id": "col_0",
      "label": "Parameter",
      "valueType": "text"
    },
    {
      "id": "col_1",
      "label": "Value",
      "valueType": "number"
    },
    {
      "id": "col_2",
      "label": "Unit",
      "valueType": "text"
    }
  ],
  "rows": [
    {
      "id": "row_0",
      "cells": {
        "col_0": "Voltage",
        "col_1": "",
        "col_2": "V"
      }
    },
    {
      "id": "row_1",
      "cells": {
        "col_0": "Current",
        "col_1": "",
        "col_2": "A"
      }
    }
  ]
}
```

Fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Unique ID of the table component. |
| `type` | string | yes | Always `table`. |
| `title` | string | yes | Table title shown to the user. |
| `columns` | array | yes | Column definitions. |
| `rows` | array | yes | Row definitions. |

Column fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Column ID, for example `col_0`. |
| `label` | string | yes | Column name shown in the table header. |
| `valueType` | string | no | Optional cell type, for example `text`, `number`, `date`, or `checkbox`. |

Row fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Row ID, for example `row_0`. |
| `cells` | object | yes | Object mapping column IDs to cell values. |



---

### 5.10 Images section object

An images section allows one or multiple uploaded images to be connected to the checklist.

Example:

```json
{
  "id": "images_machine_photos",
  "type": "imagesSection",
  "title": "Machine Photos",
  "description": "Upload photos of the inspected machine.",
  "images": [
    {
      "id": "image_001",
      "type": "imageRef",
      "label": "Front view",
      "bucket": "checklist-images",
      "path": "checklists/checklist_123/images/image_001.png",
      "mimeType": "image/png"
    }
  ]
}
```

Fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Unique ID of the images section. |
| `type` | string | yes | Always `imagesSection`. |
| `title` | string | yes | Title shown above the images. |
| `description` | string | no | Optional explanation. |
| `images` | array | yes | List of image references. |

Image reference fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | string | yes | Unique image reference ID. |
| `type` | string | yes | Always `imageRef`. |
| `label` | string | no | Optional label for the image. |
| `bucket` | string | yes | Storage bucket name. |
| `path` | string | yes | Path/key of the image in storage. |
| `mimeType` | string | yes | MIME type, for example `image/png`. |

The checklist JSON should store references to images, not the raw image file content.

---

### 5.11 PDF section or PDF reference object

A checklist may also reference PDFs, for example instruction manuals or generated reports.

Example:

```json
{
  "id": "pdf_manuals",
  "type": "pdfSection",
  "title": "Related Documents",
  "pdfs": [
    {
      "id": "pdf_001",
      "type": "pdfRef",
      "label": "Machine manual",
      "bucket": "checklist-pdfs",
      "path": "checklists/checklist_123/pdfs/manual.pdf",
      "mimeType": "application/pdf"
    }
  ]
}
```

Like images, PDFs should be stored in object storage, while the checklist JSON stores only metadata and paths.

---

### 5.12 Why every object needs an ID

Every component needs a stable ID because the AI and frontend must be able to refer to exact objects.

For example, suppose the user says:

> Change the label of the emergency stop checkbox to “Emergency stop tested successfully”.

The GenAI should not return the whole checklist. It should return something like:

```json
{
  "tool": "updateComponent",
  "targetId": "checkbox_emergency_stop",
  "patch": {
    "label": "Emergency stop tested successfully"
  }
}
```

The backend then finds the component with ID `checkbox_emergency_stop` and applies the patch.

Without IDs, the system would have to guess which object the AI means. That is fragile.

---

### 5.13 Explicit fields are better than generic `data`

Avoid this style:

```json
{
  "id": "field_001",
  "type": "textField",
  "data": {
    "label": "Operator name",
    "value": ""
  }
}
```

Prefer this style:

```json
{
  "id": "field_001",
  "type": "textField",
  "label": "Operator name",
  "value": ""
}
```

Explicit fields are easier to validate in FastAPI/Pydantic, easier to type in TypeScript, easier to render in React, and easier for AI tool calls to generate correctly.

---

## 6. Frontend architecture

### 6.1 Main frontend responsibilities

The frontend should be responsible for:

- rendering checklist JSON into UI;
- providing edit mode and use mode;
- keeping local state while the user edits;
- sending updates to the backend;
- calling AI endpoints when the user asks for AI edits;
- uploading images/PDFs through backend-supported upload flows;
- showing validation errors;
- showing loading and saving states.

---

### 6.2 Suggested frontend folder structure

A possible React structure:

```text
frontend/
└── src/
    ├── api/
    │   ├── authApi.ts
    │   ├── checklistApi.ts
    │   ├── aiApi.ts
    │   └── fileApi.ts
    │
    ├── components/
    │   ├── checklist/
    │   │   ├── ChecklistRenderer.tsx
    │   │   ├── SectionRenderer.tsx
    │   │   ├── ComponentRenderer.tsx
    │   │   ├── CheckboxContainerRenderer.tsx
    │   │   ├── TextFieldRenderer.tsx
    │   │   ├── NumericFieldRenderer.tsx
    │   │   ├── TableRenderer.tsx
    │   │   ├── ImagesSectionRenderer.tsx
    │   │   └── PdfSectionRenderer.tsx
    │   │
    │   ├── editor/
    │   │   ├── ChecklistEditPage.tsx
    │   │   ├── AddComponentMenu.tsx
    │   │   ├── ComponentSettingsPanel.tsx
    │   │   └── ReorderControls.tsx
    │   │
    │   └── ai/
    │       ├── AiAssistantPanel.tsx
    │       ├── AiPromptBox.tsx
    │       └── AiOperationPreview.tsx
    │
    ├── pages/
    │   ├── ChecklistListPage.tsx
    │   ├── ChecklistEditPage.tsx
    │   └── ChecklistUsePage.tsx
    │
    ├── types/
    │   └── checklist.ts
    │
    ├── hooks/
    │   ├── useChecklist.ts
    │   ├── useAutosaveChecklist.ts
    │   └── useAiChecklistEdit.ts
    │
    └── main.tsx
```

---

### 6.3 TypeScript checklist types

The frontend should define TypeScript types matching the JSON structure.

Example:

```ts
export type ChecklistRoot = {
  id: string;
  type: "root";
  version: number;
  title?: string;
  children: ChecklistComponent[];
};

export type SectionComponent = {
  id: string;
  type: "section";
  title: string;
  description?: string;
  children: ChecklistComponent[];
};

export type CheckboxContainerComponent = {
  id: string;
  type: "checkboxContainer";
  title: string;
  items: CheckboxItemComponent[];
};

export type CheckboxItemComponent = {
  id: string;
  type: "checkboxItem";
  label: string;
  checked: boolean;
  required?: boolean;
};

export type TextFieldComponent = {
  id: string;
  type: "textField";
  label: string;
  placeholder?: string;
  value: string;
  required?: boolean;
};

export type NumericFieldComponent = {
  id: string;
  type: "numericField";
  label: string;
  value: number | null;
  unit?: string;
  min?: number;
  max?: number;
  required?: boolean;
};

export type TableComponent = {
  id: string;
  type: "table";
  title: string;
  columns: TableColumn[];
  rows: TableRow[];
};

export type TableColumn = {
  id: string;
  label: string;
  valueType?: "text" | "number" | "date" | "checkbox";
};

export type TableRow = {
  id: string;
  cells: Record<string, string | number | boolean | null>;
};

export type ImagesSectionComponent = {
  id: string;
  type: "imagesSection";
  title: string;
  description?: string;
  images: ImageRef[];
};

export type ImageRef = {
  id: string;
  type: "imageRef";
  label?: string;
  bucket: string;
  path: string;
  mimeType: string;
};

export type PdfSectionComponent = {
  id: string;
  type: "pdfSection";
  title: string;
  pdfs: PdfRef[];
};

export type PdfRef = {
  id: string;
  type: "pdfRef";
  label?: string;
  bucket: string;
  path: string;
  mimeType: "application/pdf";
};

export type ChecklistComponent =
  | SectionComponent
  | CheckboxContainerComponent
  | TextFieldComponent
  | NumericFieldComponent
  | TableComponent
  | ImagesSectionComponent
  | PdfSectionComponent;
```

This is called a discriminated union. The `type` field tells TypeScript which object shape it is dealing with.

---

### 6.4 Rendering checklist components

The frontend should have one generic component renderer.

```tsx
function ComponentRenderer({ component }: { component: ChecklistComponent }) {
  switch (component.type) {
    case "section":
      return <SectionRenderer section={component} />;
    case "checkboxContainer":
      return <CheckboxContainerRenderer component={component} />;
    case "textField":
      return <TextFieldRenderer component={component} />;
    case "numericField":
      return <NumericFieldRenderer component={component} />;
    case "table":
      return <TableRenderer component={component} />;
    case "imagesSection":
      return <ImagesSectionRenderer component={component} />;
    case "pdfSection":
      return <PdfSectionRenderer component={component} />;
    default:
      return null;
  }
}
```

A root renderer then maps over children:

```tsx
function ChecklistRenderer({ checklist }: { checklist: ChecklistRoot }) {
  return (
    <div>
      {checklist.children.map((component) => (
        <ComponentRenderer key={component.id} component={component} />
      ))}
    </div>
  );
}
```

A section renderer also maps over children:

```tsx
function SectionRenderer({ section }: { section: SectionComponent }) {
  return (
    <section>
      <h2>{section.title}</h2>
      {section.description && <p>{section.description}</p>}

      {section.children.map((component) => (
        <ComponentRenderer key={component.id} component={component} />
      ))}
    </section>
  );
}
```

---

### 6.5 Edit mode vs use mode

The application should probably have two modes:

1. **Edit mode**
2. **Use mode**

In edit mode, the user modifies the structure of the checklist.

Examples:

- add a section;
- rename a section;
- add a text field;
- add a table;
- reorder components;
- delete components;
- ask the AI to generate or modify checklist structure.

In use mode, the user fills out the checklist.

Examples:

- check checkboxes;
- enter text values;
- enter numeric measurements;
- upload images;
- attach PDFs;
- complete the checklist.

The same JSON structure can support both modes, but the UI behavior is different.

In edit mode, clicking a component might open settings.

In use mode, clicking a checkbox changes its checked value.

---

### 6.6 Updating frontend state

When the user manually edits a field in the frontend, the frontend should update its local checklist JSON state.

For example:

```tsx
function handleTextFieldChange(componentId: string, newValue: string) {
  setChecklist((previousChecklist) =>
    updateComponentInTree(previousChecklist, componentId, {
      value: newValue,
    })
  );
}
```

The helper function `updateComponentInTree` recursively searches the JSON tree for the component with the given ID and applies the patch.

After updating local state, the frontend can save changes to the backend.

There are two possible save strategies:

1. Save immediately after every change.
2. Save with debounce/autosave.

For a proof of concept, a debounced autosave is usually a good idea.

Example:

```text
User types into field
   ↓
Frontend updates local JSON immediately
   ↓
Frontend waits 500–1000 ms
   ↓
Frontend sends PUT /api/checklists/{id}
   ↓
Backend validates and saves JSONB in database
```

---

### 6.7 Frontend API calls

The frontend should centralize API calls in files like `checklistApi.ts`.

Example:

```ts
export async function getChecklist(checklistId: string) {
  const response = await fetch(`/api/checklists/${checklistId}`);

  if (!response.ok) {
    throw new Error("Failed to load checklist");
  }

  return response.json();
}
```

Creating a checklist:

```ts
export async function createChecklist(title: string) {
  const response = await fetch("/api/checklists", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw new Error("Failed to create checklist");
  }

  return response.json();
}
```

Saving a checklist:

```ts
export async function updateChecklist(checklistId: string, content: ChecklistRoot) {
  const response = await fetch(`/api/checklists/${checklistId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    throw new Error("Failed to save checklist");
  }

  return response.json();
}
```

---

## 7. Backend architecture with FastAPI

### 7.1 Main backend responsibilities

The backend should handle:

- API routing;
- authentication;
- request validation;
- database access;
- checklist JSON validation;
- storage path handling;
- image/PDF metadata;
- GenAI API calls;
- AI structured output validation;
- applying AI operations safely;
- returning responses to the frontend.

---

### 7.2 Suggested backend folder structure

A possible FastAPI structure:

```text
backend/
└── app/
    ├── main.py
    │
    ├── core/
    │   ├── config.py
    │   └── security.py
    │
    ├── db/
    │   ├── session.py
    │   └── models.py
    │
    ├── auth/
    │   ├── router.py
    │   ├── schemas.py
    │   └── service.py
    │
    ├── checklists/
    │   ├── router.py
    │   ├── schemas.py
    │   ├── service.py
    │   └── repository.py
    │
    ├── ai/
    │   ├── router.py
    │   ├── schemas.py
    │   ├── service.py
    │   ├── gemini_client.py
    │   ├── prompts.py
    │   └── operations.py
    │
    ├── files/
    │   ├── router.py
    │   ├── schemas.py
    │   ├── service.py
    │   └── storage_client.py
    │
    └── checklist_json/
        ├── models.py
        ├── validation.py
        └── tree_operations.py
```

Explanation:

| Folder | Purpose |
|---|---|
| `core` | App configuration, environment variables, security helpers. |
| `db` | Database session and SQLAlchemy models. |
| `auth` | Register/login/me endpoints. |
| `checklists` | Checklist CRUD endpoints and business logic. |
| `ai` | GenAI endpoints, prompts, structured output parsing, tool calls. |
| `files` | Image/PDF upload and storage logic. |
| `checklist_json` | Pydantic models and helper functions for checklist JSON. |

---

### 7.3 What FastAPI does

FastAPI lets us define API endpoints as Python functions.

Example:

```py
from fastapi import APIRouter

router = APIRouter(prefix="/api/checklists", tags=["checklists"])

@router.get("/{checklist_id}")
def get_checklist(checklist_id: str):
    return {
        "id": checklist_id,
        "title": "Example Checklist"
    }
```

When the frontend sends:

```http
GET /api/checklists/123
```

FastAPI calls the Python function `get_checklist("123")` and returns the result as JSON.

---

### 7.4 Pydantic schemas

FastAPI uses Pydantic models to validate request and response data.

Example:

```py
from pydantic import BaseModel

class CreateChecklistRequest(BaseModel):
    title: str
```

Endpoint:

```py
@router.post("")
def create_checklist(request: CreateChecklistRequest):
    return checklist_service.create_checklist(title=request.title)
```

If the frontend sends invalid data, FastAPI automatically returns a validation error.

For example, this is invalid because `title` is missing:

```json
{
  "name": "Wrong field"
}
```

FastAPI would reject it before it reaches the service logic.

---

## 8. Necessary backend endpoints

### 8.1 Authentication endpoints

Even if only the backend talks directly to the database, authentication is still useful because the backend needs to know which user is making a request.

Planned endpoints:

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/me
```

#### `POST /api/auth/register`

Creates a new user.

Request:

```json
{
  "email": "user@example.com",
  "password": "plain-text-password"
}
```

Backend behavior:

- validate email/password;
- hash the password using bcrypt/argon2;
- save user in database;
- return user information or token.

Important: the plain password is never stored. Only a password hash is stored.

#### `POST /api/auth/login`

Logs the user in.

Request:

```json
{
  "email": "user@example.com",
  "password": "plain-text-password"
}
```

Backend behavior:

- find user by email;
- compare submitted password with stored password hash;
- create JWT access token;
- return token to frontend.

Response:

```json
{
  "accessToken": "jwt-token-here",
  "tokenType": "bearer"
}
```

#### `GET /api/me`

Returns the current logged-in user.

The frontend sends the JWT in the `Authorization` header:

```http
Authorization: Bearer jwt-token-here
```

Response:

```json
{
  "id": "user_123",
  "email": "user@example.com"
}
```

---

### 8.2 Checklist CRUD endpoints

CRUD means:

- Create
- Read
- Update
- Delete

Planned endpoints:

```text
GET    /api/checklists
POST   /api/checklists
GET    /api/checklists/{checklist_id}
PUT    /api/checklists/{checklist_id}
DELETE /api/checklists/{checklist_id}
```

#### `GET /api/checklists`

Returns all checklists owned by the current user.

Response:

```json
[
  {
    "id": "checklist_123",
    "title": "Machine Inspection Checklist",
    "createdAt": "2026-05-16T12:00:00Z",
    "updatedAt": "2026-05-16T12:30:00Z"
  }
]
```

This endpoint should return metadata only, not necessarily the full checklist JSON for every checklist.

#### `POST /api/checklists`

Creates a new checklist.

Request:

```json
{
  "title": "Machine Inspection Checklist"
}
```

Backend creates a default checklist JSON:

```json
{
  "id": "root",
  "type": "root",
  "version": 1,
  "title": "Machine Inspection Checklist",
  "children": []
}
```

Response:

```json
{
  "id": "checklist_123",
  "title": "Machine Inspection Checklist",
  "content": {
    "id": "root",
    "type": "root",
    "version": 1,
    "title": "Machine Inspection Checklist",
    "children": []
  }
}
```

#### `GET /api/checklists/{checklist_id}`

Loads one checklist, including its full JSON content.

Response:

```json
{
  "id": "checklist_123",
  "title": "Machine Inspection Checklist",
  "content": {
    "id": "root",
    "type": "root",
    "version": 1,
    "children": []
  },
  "createdAt": "2026-05-16T12:00:00Z",
  "updatedAt": "2026-05-16T12:30:00Z"
}
```

#### `PUT /api/checklists/{checklist_id}`

Saves an updated checklist JSON.

Request:

```json
{
  "title": "Updated Machine Inspection Checklist",
  "content": {
    "id": "root",
    "type": "root",
    "version": 1,
    "children": []
  }
}
```

Backend behavior:

- check that the user owns the checklist;
- validate the JSON structure;
- save it in the database as JSONB;
- update `updated_at` timestamp;
- return updated checklist.

#### `DELETE /api/checklists/{checklist_id}`

Deletes a checklist.

Backend behavior:

- check ownership;
- delete checklist row;
- optionally delete related file metadata;
- optionally delete associated files from storage;
- return success response.

---

### 8.3 AI checklist endpoints

Planned endpoints:

```text
POST /api/ai/checklists/{checklist_id}/edit
POST /api/ai/checklists/{checklist_id}/create-from-text
POST /api/ai/checklists/{checklist_id}/preview-operation
POST /api/ai/checklists/{checklist_id}/apply-operation
```

The minimal proof of concept only needs:

```text
POST /api/ai/checklists/{checklist_id}/edit
POST /api/ai/checklists/{checklist_id}/create-from-text
```

The preview/apply split is useful if we want the user to approve AI changes before applying them.

#### `POST /api/ai/checklists/{checklist_id}/edit`

The user asks the AI to edit an existing checklist.

Request:

```json
{
  "prompt": "Add a safety checks section with three checkbox items.",
  "mode": "apply"
}
```

Backend behavior:

1. Load current checklist from database.
2. Build a GenAI prompt containing:
   - the user's instruction;
   - the current checklist JSON or relevant part of it;
   - the allowed component schema;
   - the allowed tool calls.
3. Call the GenAI API.
4. Receive structured output.
5. Validate the output.
6. Apply the operation to the checklist JSON.
7. Save the updated checklist.
8. Return the updated checklist and operation summary.

Response:

```json
{
  "operation": {
    "tool": "addComponent",
    "targetContainerId": "root",
    "component": {
      "id": "section_safety_checks",
      "type": "section",
      "title": "Safety Checks",
      "children": [
        {
          "id": "checkbox_container_safety",
          "type": "checkboxContainer",
          "title": "Required safety checks",
          "items": [
            {
              "id": "checkbox_emergency_stop",
              "type": "checkboxItem",
              "label": "Emergency stop button works",
              "checked": false
            }
          ]
        }
      ]
    }
  },
  "checklist": {
    "id": "checklist_123",
    "content": {}
  }
}
```

#### `POST /api/ai/checklists/{checklist_id}/create-from-text`

Creates an initial checklist structure from a natural language description.

Request:

```json
{
  "prompt": "Create a machine inspection checklist with general information, safety checks, measurements, and photo documentation."
}
```

Backend behavior:

- call GenAI with a checklist generation prompt;
- ask GenAI to return a full valid initial checklist JSON;
- validate the generated JSON;
- save it as the checklist content.

This endpoint is different from edit because initial generation may reasonably return a full checklist object. After the checklist exists, future edits should preferably use smaller tool-call operations.

---

### 8.4 File upload endpoints

Planned endpoints:

```text
POST   /api/checklists/{checklist_id}/files/upload-url
POST   /api/checklists/{checklist_id}/files/register
GET    /api/checklists/{checklist_id}/files
DELETE /api/checklists/{checklist_id}/files/{file_id}
```

There are two possible upload approaches.

#### Option A: Upload through backend

Frontend sends file directly to backend. Backend uploads it to storage.

Simple, but backend handles file bytes.

Endpoint could be:

```text
POST /api/checklists/{checklist_id}/files
```

with multipart form data.

#### Option B: Signed upload URL

Frontend asks backend for a signed upload URL. Frontend uploads the file directly to storage. Backend then stores metadata.

This is cleaner for larger files.

Flow:

```text
Frontend asks backend for upload URL
   ↓
Backend creates storage path and signed URL
   ↓
Frontend uploads file directly to storage
   ↓
Frontend tells backend upload completed
   ↓
Backend saves file metadata in database
```

#### `POST /api/checklists/{checklist_id}/files/upload-url`

Request:

```json
{
  "fileName": "machine-photo.png",
  "mimeType": "image/png",
  "fileKind": "image"
}
```

Response:

```json
{
  "fileId": "file_123",
  "bucket": "checklist-images",
  "path": "checklists/checklist_123/images/file_123.png",
  "uploadUrl": "signed-upload-url"
}
```

Important: paths do not magically exist as folders in S3-like storage. Object storage uses keys. A path like `checklists/checklist_123/images/file_123.png` is just the key/name under which the object is stored. The visual folder structure is created implicitly by the key prefix.

#### `POST /api/checklists/{checklist_id}/files/register`

After the upload succeeds, the frontend calls this endpoint to register the file.

Request:

```json
{
  "fileId": "file_123",
  "componentId": "images_machine_photos",
  "bucket": "checklist-images",
  "path": "checklists/checklist_123/images/file_123.png",
  "fileName": "machine-photo.png",
  "mimeType": "image/png",
  "fileKind": "image"
}
```

Backend behavior:

- save metadata in `files` table;
- optionally update checklist JSON to include an image reference;
- return saved metadata.

---

## 9. GenAI structured output and tool calls

### 9.1 Why not let the AI return the whole checklist every time?

A dangerous design would be:

```text
Frontend sends checklist + prompt
   ↓
AI returns entire modified checklist JSON
   ↓
Backend saves entire returned JSON
```

This is risky because:

- the AI might accidentally remove components;
- the AI might overwrite user-filled values;
- the AI might hallucinate invalid fields;
- the AI might reorder unrelated sections;
- the user might not notice a subtle destructive change;
- large checklists make full-object editing more error-prone.

Instead, the AI should return explicit operations.

Good design:

```text
User prompt
   ↓
Backend gives AI allowed tools + current context
   ↓
AI returns structured tool call
   ↓
Backend validates tool call
   ↓
Backend applies operation deterministically
   ↓
Backend saves updated checklist
```

The AI proposes what to do. The backend actually does it.

---

### 9.2 Allowed AI operations

For the proof of concept, we can start with:

```text
addComponent
updateComponent
deleteComponent
moveComponent
undoLastChange
```

---

### 9.3 `addComponent` tool call

Adds a component to a container such as root or section.

Example:

```json
{
  "tool": "addComponent",
  "targetContainerId": "section_general_info",
  "position": "end",
  "component": {
    "id": "text_operator_name",
    "type": "textField",
    "label": "Operator name",
    "placeholder": "Enter operator name",
    "value": "",
    "required": true
  }
}
```

Fields:

| Field | Meaning |
|---|---|
| `tool` | Name of operation. |
| `targetContainerId` | ID of the parent container. |
| `position` | Where to insert: `start`, `end`, or numeric index. |
| `component` | New component object to insert. |

Backend validation:

- target container exists;
- target container supports children;
- component has valid schema;
- component ID is unique;
- insertion position is valid.

---

### 9.4 `updateComponent` tool call

Updates selected fields of an existing component.

Example:

```json
{
  "tool": "updateComponent",
  "targetId": "text_operator_name",
  "patch": {
    "label": "Technician name",
    "required": true
  }
}
```

Backend validation:

- target component exists;
- patch only includes allowed fields;
- patch does not change immutable fields like `id` or usually `type`;
- updated component still passes schema validation.

The backend should not blindly merge any arbitrary patch into the JSON.

---

### 9.5 `deleteComponent` tool call

Deletes a component by ID.

Example:

```json
{
  "tool": "deleteComponent",
  "targetId": "text_old_field"
}
```

Backend validation:

- target component exists;
- deleting it does not break the checklist;
- deletion is allowed for that component type.

It may be useful to prevent deleting the root object.

---

### 9.6 `moveComponent` tool call

Moves a component from one container to another or changes its order.

Example:

```json
{
  "tool": "moveComponent",
  "targetId": "table_measurements",
  "newParentId": "section_measurements",
  "position": 1
}
```

Backend validation:

- target component exists;
- new parent exists;
- new parent supports children;
- move would not create circular nesting;
- position is valid.

---

### 9.7 Table-specific tool calls

Tables are slightly different because rows and columns are inside a table.

Example: add table row

```json
{
  "tool": "addTableRow",
  "tableId": "table_measurements",
  "row": {
    "id": "row_2",
    "cells": {
      "col_0": "Pressure",
      "col_1": "",
      "col_2": "bar"
    }
  }
}
```

Example: add table column

```json
{
  "tool": "addTableColumn",
  "tableId": "table_measurements",
  "column": {
    "id": "col_3",
    "label": "Comment",
    "valueType": "text"
  },
  "defaultValue": ""
}
```

When a column is added, each existing row should receive a default cell value for that column.

---

### 9.8 AI response schema

The backend should request a strict structured response from the GenAI API.

A generic response envelope could look like this:

```json
{
  "messageToUser": "I added a safety checks section with three items.",
  "operations": [
    {
      "tool": "addComponent",
      "targetContainerId": "root",
      "position": "end",
      "component": {
        "id": "section_safety_checks",
        "type": "section",
        "title": "Safety Checks",
        "children": []
      }
    }
  ]
}
```

Using `operations` as a list allows the AI to perform multiple changes in one request.

The backend should apply them one by one, validating after each step or validating the final result after all operations.

---

### 9.9 Backend-side operation application

The backend should have deterministic functions like:

```python
def apply_operation(checklist: dict, operation: dict) -> dict:
    match operation["tool"]:
        case "addComponent":
            return add_component(checklist, operation)
        case "updateComponent":
            return update_component(checklist, operation)
        case "deleteComponent":
            return delete_component(checklist, operation)
        case "moveComponent":
            return move_component(checklist, operation)
        case _:
            raise ValueError("Unsupported operation")
```

The GenAI should never directly modify the database. It only returns proposed structured operations. The backend is responsible for applying them.

---

### 9.10 AI edit flow

Full flow:

```text
User writes prompt in frontend
   ↓
Frontend calls POST /api/ai/checklists/{id}/edit
   ↓
Backend loads checklist JSON from database
   ↓
Backend sends checklist context + allowed tools to GenAI
   ↓
GenAI returns structured operations
   ↓
Backend validates operations
   ↓
Backend applies operations to checklist JSON
   ↓
Backend saves updated JSONB in database
   ↓
Backend returns updated checklist to frontend
   ↓
Frontend re-renders checklist
```

---

### 9.11 Preview before applying AI operations

A safer UX is to preview AI operations before applying them.

Flow:

```text
User asks AI for change
   ↓
Backend gets AI operation
   ↓
Frontend displays preview: "Add section Safety Checks"
   ↓
User clicks Apply
   ↓
Frontend calls apply endpoint
   ↓
Backend applies operation
```

For the proof of concept, automatic apply is simpler. But preview mode is better for trust and safety.

---

## 10. Database design

### 10.1 Database choice

The planned database can be PostgreSQL, either directly hosted or through a service like Supabase.

PostgreSQL is a good fit because it supports:

- normal relational tables;
- JSONB columns for structured JSON;
- indexes;
- foreign keys;
- timestamps;
- UUIDs.

The checklist content should be stored as `jsonb`.

---

### 10.2 Planned tables

Recommended first set of tables:

```text
users
checklists
checklist_versions or checklist_snapshots
files
```

Optional later tables:

```text
checklist_runs
checklist_run_values
ai_edit_logs
```

For the proof of concept, the most important tables are `users`, `checklists`, and `files`.

---

### 10.3 `users` table

Stores application users.

Example schema:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Fields:

| Column | Meaning |
|---|---|
| `id` | Unique user ID. |
| `email` | User email. |
| `password_hash` | Hashed password. Never store plain passwords. |
| `created_at` | Creation timestamp. |
| `updated_at` | Last update timestamp. |

Password hashes should be stored as strings in the format produced by the password hashing library.

For example, bcrypt hashes are stored as strings like:

```text
$2b$12$...
```

The exact format depends on the hashing algorithm/library.

---

### 10.4 `checklists` table

Stores checklist metadata and the actual checklist JSON.

Example schema:

```sql
CREATE TABLE checklists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{"id":"root","type":"root","version":1,"children":[]}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Fields:

| Column | Meaning |
|---|---|
| `id` | Unique checklist ID. |
| `owner_id` | User who owns the checklist. |
| `title` | Checklist title. |
| `content` | Full checklist JSON stored as JSONB. |
| `created_at` | Creation timestamp. |
| `updated_at` | Last update timestamp. |

Why JSONB?

- The checklist structure is flexible.
- Different components have different fields.
- PostgreSQL can store JSONB efficiently.
- The backend can retrieve the full JSON, validate it, modify it, and save it back.

---

### 10.5 `checklist_snapshots` table

This table is useful for undo functionality.

Simpler design:

```sql
CREATE TABLE checklist_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checklist_id UUID NOT NULL REFERENCES checklists(id) ON DELETE CASCADE,
    content JSONB NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Before applying an AI operation, the backend can save the previous checklist content as a snapshot.

Then `undoLastChange` can restore the most recent snapshot.

For a proof of concept, it is enough to store only the latest previous snapshot in the `checklists` table itself:

```sql
ALTER TABLE checklists ADD COLUMN previous_content JSONB;
```

But a separate snapshot table is cleaner and more extensible.

---

### 10.6 `files` table

Stores metadata for images and PDFs.

Example schema:

```sql
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checklist_id UUID NOT NULL REFERENCES checklists(id) ON DELETE CASCADE,
    component_id TEXT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_kind TEXT NOT NULL CHECK (file_kind IN ('image', 'pdf')),
    bucket TEXT NOT NULL,
    path TEXT NOT NULL,
    original_file_name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Fields:

| Column | Meaning |
|---|---|
| `id` | Unique file metadata ID. |
| `checklist_id` | Checklist this file belongs to. |
| `component_id` | Optional checklist component this file is attached to. |
| `owner_id` | User who uploaded the file. |
| `file_kind` | `image` or `pdf`. |
| `bucket` | Storage bucket name. |
| `path` | Path/key in storage. |
| `original_file_name` | Original filename from user upload. |
| `mime_type` | File MIME type. |
| `size_bytes` | Optional file size. |
| `created_at` | Upload timestamp. |

The checklist JSON can reference a file by bucket/path and optionally by `fileId`.

Example:

```json
{
  "id": "image_001",
  "type": "imageRef",
  "fileId": "file_123",
  "bucket": "checklist-images",
  "path": "checklists/checklist_123/images/file_123.png",
  "mimeType": "image/png"
}
```

---

### 10.7 Optional `ai_edit_logs` table

This table records AI prompts and operations.

Example schema:

```sql
CREATE TABLE ai_edit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checklist_id UUID NOT NULL REFERENCES checklists(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    operations JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

This is useful for debugging and explaining what the AI changed.

It can also help with undo/history later.

---

### 10.8 Optional checklist run tables

A later version may separate checklist templates from checklist executions.

For example:

- `checklists` stores the template.
- `checklist_runs` stores one filled-out execution of a checklist.

Example:

```sql
CREATE TABLE checklist_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checklist_id UUID NOT NULL REFERENCES checklists(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'in_progress',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

This is useful if the same checklist template is used many times.

For the proof of concept, we can initially store everything in `checklists.content` and introduce runs later.

---

## 11. Storage buckets for images and PDFs

### 11.1 Why use storage buckets?

Images and PDFs are binary files. They should not be stored directly inside the JSONB checklist column.

Instead:

- upload the file to object storage;
- store metadata in the database;
- store a reference in the checklist JSON.

This keeps the database cleaner and prevents large binary files from bloating checklist JSON.

---

### 11.2 Planned buckets

Recommended buckets:

```text
checklist-images
checklist-pdfs
```

Using two buckets makes it easier to apply different validation rules and access policies.

For example:

- `checklist-images` only allows image MIME types like `image/png`, `image/jpeg`, `image/webp`.
- `checklist-pdfs` only allows `application/pdf`.

A single bucket with folders could also work, but two buckets are clearer for the proof of concept.

---

### 11.3 Recommended storage paths

Images:

```text
checklists/{checklist_id}/images/{file_id}.{extension}
```

PDFs:

```text
checklists/{checklist_id}/pdfs/{file_id}.pdf
```

Example image path:

```text
checklists/6a4f.../images/9b12....png
```

Example PDF path:

```text
checklists/6a4f.../pdfs/7c34....pdf
```

Do not rely on original filenames as storage paths. Original filenames can contain spaces, duplicates, or unsafe characters.

Better:

- generate a unique file ID;
- use that ID in the storage path;
- store the original filename separately in the database.

---

### 11.4 Do storage paths get created automatically?

In S3-like object storage, folders are not real folders in the traditional filesystem sense.

A path like this:

```text
checklists/checklist_123/images/image_001.png
```

is simply the object key.

When a file is uploaded with that key, the storage UI may display it as if the folders `checklists/`, `checklist_123/`, and `images/` exist. But they are just prefixes in the object key.

So the backend does not usually need to create folders manually. It just uploads the file using the desired path/key.

---

## 12. Auth and JWT overview

### 12.1 Why auth is needed

Even if only the backend talks to the database, authentication is still needed because the backend must know which user is making each request.

Without auth, any user could request any checklist ID.

Auth lets the backend enforce rules like:

```text
User A can only read/update/delete User A's checklists.
User B cannot access User A's checklists.
```

---

### 12.2 JWT mental model

JWT stands for JSON Web Token.

After login, the backend creates a token containing claims such as:

```json
{
  "sub": "user_123",
  "exp": 1770000000
}
```

The backend signs this token with a secret key.

The frontend stores the token and sends it in future requests:

```http
Authorization: Bearer jwt-token-here
```

The backend verifies the signature and extracts the user ID from `sub`.

Important: a JWT is usually signed, not encrypted. The payload is not secret. Do not put passwords or sensitive private data inside the JWT payload.

---

## 13. End-to-end flows

### 13.1 Creating a checklist manually

```text
User clicks "New Checklist"
   ↓
Frontend calls POST /api/checklists
   ↓
Backend creates row in checklists table with default JSONB
   ↓
Backend returns checklist
   ↓
Frontend navigates to edit page
```

---

### 13.2 Editing a checklist manually

```text
User adds a text field in frontend
   ↓
Frontend updates local checklist JSON state
   ↓
Frontend calls PUT /api/checklists/{id}
   ↓
Backend validates checklist JSON
   ↓
Backend saves JSONB in database
   ↓
Frontend shows saved state
```

---

### 13.3 Editing a checklist with AI

```text
User writes: "Add a measurements table"
   ↓
Frontend calls POST /api/ai/checklists/{id}/edit
   ↓
Backend loads checklist JSON
   ↓
Backend sends prompt + current JSON + allowed tools to GenAI
   ↓
GenAI returns addComponent operation
   ↓
Backend validates operation
   ↓
Backend applies operation
   ↓
Backend saves updated JSONB
   ↓
Frontend receives updated checklist
   ↓
Frontend re-renders checklist
```

---

### 13.4 Uploading an image

```text
User selects image file
   ↓
Frontend asks backend for upload URL
   ↓
Backend creates file ID and storage path
   ↓
Frontend uploads image to storage
   ↓
Frontend calls backend to register file metadata
   ↓
Backend saves file metadata in files table
   ↓
Backend updates checklist JSON with image reference
   ↓
Frontend displays image
```

---

### 13.5 Uploading a PDF

```text
User selects PDF file
   ↓
Frontend asks backend for upload URL
   ↓
Backend creates file ID and storage path in checklist-pdfs bucket
   ↓
Frontend uploads PDF
   ↓
Frontend registers file metadata
   ↓
Backend stores PDF reference
   ↓
Frontend displays link/preview
```

---

## 14. Validation strategy

### 14.1 Frontend validation

The frontend should validate basic user input for good UX.

Examples:

- required field is empty;
- numeric field contains invalid value;
- unsupported file type selected;
- table column label is empty.

Frontend validation improves usability but is not enough for security.

---

### 14.2 Backend validation

The backend must validate everything again.

Backend validation should include:

- request body shape;
- checklist JSON schema;
- component IDs are unique;
- component types are valid;
- file MIME types are allowed;
- user owns the checklist;
- AI operation is valid before applying it.

Never trust the frontend and never blindly trust AI output.

---

### 14.3 GenAI output validation

GenAI output must be treated as untrusted data.

The backend should validate:

- output is valid JSON;
- operation names are allowed;
- required fields exist;
- target IDs exist;
- new components follow schema;
- patches only include allowed fields;
- operation does not delete or corrupt root;
- final checklist still validates.

---

## 15. Minimal proof-of-concept scope

To keep the project manageable, the first version can include only:

### Frontend

- Checklist list page.
- Checklist edit page.
- Checklist use page.
- JSON-based renderer.
- Add/edit/delete basic components manually.
- AI prompt panel.
- Image/PDF upload UI.

### Checklist components

- Section.
- Checkbox container.
- Checkbox item.
- Text field.
- Numeric field.
- Table.
- Images section.
- PDF section.

### Backend

- Auth endpoints.
- Checklist CRUD endpoints.
- AI edit endpoint.
- File upload/register endpoints.
- JSON validation.
- Database persistence.

### Database

- `users`.
- `checklists`.
- `files`.
- optional `checklist_snapshots`.

### Storage

- `checklist-images` bucket.
- `checklist-pdfs` bucket.

### AI tools

- `addComponent`.
- `updateComponent`.
- `deleteComponent`.
- `moveComponent`.
- optional `undoLastChange`.

---

## 16. Recommended implementation order

A practical order for the team:

1. Define final checklist JSON schema.
2. Create TypeScript types in frontend.
3. Build static renderer for sample JSON.
4. Build FastAPI checklist CRUD endpoints.
5. Store checklist JSONB in PostgreSQL.
6. Connect frontend to backend.
7. Add manual edit operations in frontend.
8. Add file upload metadata and storage bucket support.
9. Add AI edit endpoint.
10. Implement backend operation application logic.
11. Add frontend AI prompt panel.
12. Add undo/snapshot support.
13. Polish validation and error handling.

This order avoids starting with the AI too early. The checklist JSON model and deterministic edit operations should work before GenAI is connected.

---

## 17. Key design rules to remember

1. Store checklist structure as JSONB, not HTML.
2. Every checklist object needs an `id` and a `type`.
3. The `type` field controls frontend rendering and backend validation.
4. The AI should not rewrite the full checklist for normal edits.
5. The AI should return structured tool calls.
6. The backend validates and applies AI operations.
7. Images and PDFs go into storage buckets, not directly into JSONB.
8. The database stores file metadata and checklist JSON references.
9. The frontend renders the checklist dynamically from JSON.
10. FastAPI endpoints are the contract between frontend and backend.

---

## 18. Example complete checklist JSON

```json
{
  "id": "root",
  "type": "root",
  "version": 1,
  "title": "Machine Inspection Checklist",
  "children": [
    {
      "id": "section_general_info",
      "type": "section",
      "title": "General Information",
      "children": [
        {
          "id": "text_operator_name",
          "type": "textField",
          "label": "Operator name",
          "placeholder": "Enter operator name",
          "value": "",
          "required": true
        },
        {
          "id": "number_machine_hours",
          "type": "numericField",
          "label": "Machine operating hours",
          "value": null,
          "unit": "h"
        }
      ]
    },
    {
      "id": "section_safety",
      "type": "section",
      "title": "Safety Checks",
      "children": [
        {
          "id": "checkbox_container_safety",
          "type": "checkboxContainer",
          "title": "Required checks",
          "items": [
            {
              "id": "checkbox_emergency_stop",
              "type": "checkboxItem",
              "label": "Emergency stop button works",
              "checked": false,
              "required": true
            },
            {
              "id": "checkbox_guard_installed",
              "type": "checkboxItem",
              "label": "Protective guard is installed",
              "checked": false,
              "required": true
            }
          ]
        }
      ]
    },
    {
      "id": "section_measurements",
      "type": "section",
      "title": "Measurements",
      "children": [
        {
          "id": "table_measurements",
          "type": "table",
          "title": "Electrical Measurements",
          "columns": [
            {
              "id": "col_0",
              "label": "Parameter",
              "valueType": "text"
            },
            {
              "id": "col_1",
              "label": "Value",
              "valueType": "number"
            },
            {
              "id": "col_2",
              "label": "Unit",
              "valueType": "text"
            }
          ],
          "rows": [
            {
              "id": "row_0",
              "cells": {
                "col_0": "Voltage",
                "col_1": "",
                "col_2": "V"
              }
            },
            {
              "id": "row_1",
              "cells": {
                "col_0": "Current",
                "col_1": "",
                "col_2": "A"
              }
            }
          ]
        }
      ]
    },
    {
      "id": "section_documentation",
      "type": "section",
      "title": "Documentation",
      "children": [
        {
          "id": "images_machine_photos",
          "type": "imagesSection",
          "title": "Machine Photos",
          "description": "Upload photos of the inspected machine.",
          "images": []
        },
        {
          "id": "pdf_related_documents",
          "type": "pdfSection",
          "title": "Related PDFs",
          "pdfs": []
        }
      ]
    }
  ]
}
```

---

## 19. Final summary

The most important part of this project is the checklist JSON model. Everything else depends on it.

The frontend renders this JSON into an interactive checklist. The backend stores and validates this JSON. The database persists it as JSONB. The AI modifies it through structured tool calls. Images and PDFs live in storage buckets and are referenced from the JSON and the files table.

The safest design is not to let the AI directly overwrite the entire checklist after every prompt. Instead, the AI should return small, explicit operations such as `addComponent`, `updateComponent`, `deleteComponent`, and `moveComponent`. The backend should validate those operations and apply them deterministically.

This gives the project a clear architecture:

```text
React frontend renders and edits checklist JSON
FastAPI backend validates and saves checklist JSON
PostgreSQL stores checklist JSONB and metadata
Storage buckets store images and PDFs
GenAI returns structured tool calls
Backend applies AI operations safely
```

That architecture should be understandable, implementable, and robust enough for a proof-of-concept AI checklist web application.
