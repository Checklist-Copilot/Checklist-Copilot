# Checklist Component Structure

This document defines the JSON shape for every component that can appear inside a checklist.
All components share a common base, then extend it with type-specific fields.

---

## Common Base Fields

Every component, regardless of type, carries these fields:

| Field           | Type   | Required | Description                                                   |
|-----------------|--------|----------|---------------------------------------------------------------|
| `id`            | string | yes      | Globally unique identifier (UUIDv7). Never changes.           |
| `humanReadableId` | string | no    | Stable snake_case name for AI and script references.          |
| `type`          | string | yes      | One of the type strings listed below.                         |
| `label`         | string | yes      | Human-visible display text for the component.                 |

---

## Root Document

The checklist document itself is the root node. It is not a component that can be added or removed; it is always present as the top-level object.

```json
{
  "id": "root",
  "type": "root",
  "children": [ /* top-level components */ ]
}
```

`children` accepts any component except `checkbox` (which must always be inside a `checkboxGroup`).

---

## 1. Section

**Type string:** `section`

A labelled container that groups related components. Sections can be nested.

```json
{
  "id": "string (UUIDv7)",
  "humanReadableId": "string | null",
  "type": "section",
  "label": "string",
  "collapsed": false,
  "children": [ /* any components except checkbox */ ]
}
```

| Field       | Type    | Required | Default | Description                              |
|-------------|---------|----------|---------|------------------------------------------|
| `collapsed` | boolean | no       | `false` | Whether the section is collapsed in UI.  |
| `children`  | array   | yes      | `[]`    | Child components.                        |

**Valid parents:** root checklist, another section.  
**Valid children:** any component except `checkbox`.

---

## 2. Checkbox Container

**Type string:** `checkboxGroup`

A labelled group of checkbox items. The group itself does not have a checked state.

```json
{
  "id": "string (UUIDv7)",
  "humanReadableId": "string | null",
  "type": "checkboxGroup",
  "label": "string",
  "items": [ /* checkbox components */ ]
}
```

| Field   | Type  | Required | Default | Description            |
|---------|-------|----------|---------|------------------------|
| `items` | array | yes      | `[]`    | List of checkbox items.|

**Valid parents:** root checklist, section.  
**Valid children:** `checkbox` only.

---

## 3. Checkbox Item

**Type string:** `checkbox`

A single checkable item. Must always live inside a `checkboxGroup`.

```json
{
  "id": "string (UUIDv7)",
  "humanReadableId": "string | null",
  "type": "checkbox",
  "label": "string",
  "checked": false,
  "required": false
}
```

| Field      | Type    | Required | Default | Description                                    |
|------------|---------|----------|---------|------------------------------------------------|
| `checked`  | boolean | yes      | `false` | Current checked state.                         |
| `required` | boolean | no       | `false` | Must be checked before the checklist can be submitted. |

**Valid parents:** `checkboxGroup` only.  
**Valid children:** none (leaf node).

---

## 4. Text Field

**Type string:** `textField`

A free-text input. Can be single-line or multi-line.

```json
{
  "id": "string (UUIDv7)",
  "humanReadableId": "string | null",
  "type": "textField",
  "label": "string",
  "value": "",
  "placeholder": "string | null",
  "required": false,
  "multiline": false
}
```

| Field         | Type    | Required | Default | Description                            |
|---------------|---------|----------|---------|----------------------------------------|
| `value`       | string  | yes      | `""`    | Current value entered by the user.     |
| `placeholder` | string  | no       | `null`  | Hint text shown when the field is empty.|
| `required`    | boolean | no       | `false` | Field must be filled before submission.|
| `multiline`   | boolean | no       | `false` | Renders as a textarea if `true`.       |

**Valid parents:** root checklist, section.  
**Valid children:** none (leaf node).

---

## 5. Numeric Field

**Type string:** `numberField`

A numeric input with optional unit and range constraints.

```json
{
  "id": "string (UUIDv7)",
  "humanReadableId": "string | null",
  "type": "numberField",
  "label": "string",
  "value": null,
  "unit": "string | null",
  "min": null,
  "max": null,
  "required": false
}
```

| Field      | Type           | Required | Default | Description                                   |
|------------|----------------|----------|---------|-----------------------------------------------|
| `value`    | number \| null | yes      | `null`  | Current numeric value.                        |
| `unit`     | string         | no       | `null`  | Display unit appended to the input (e.g. `"°C"`, `"kg"`). |
| `min`      | number \| null | no       | `null`  | Minimum allowed value (inclusive).            |
| `max`      | number \| null | no       | `null`  | Maximum allowed value (inclusive).            |
| `required` | boolean        | no       | `false` | Field must be filled before submission.       |

**Valid parents:** root checklist, section.  
**Valid children:** none (leaf node).

---

## 6. Images Container

**Type string:** `imageBlock`

Displays one or more reference images and/or allows the user to upload photos.

```json
{
  "id": "string (UUIDv7)",
  "humanReadableId": "string | null",
  "type": "imageBlock",
  "label": "string",
  "images": [
    {
      "imageId": "string (UUIDv7)",
      "url": "string",
      "caption": "string | null"
    }
  ],
  "allowUpload": false
}
```

| Field         | Type    | Required | Default | Description                                         |
|---------------|---------|----------|---------|-----------------------------------------------------|
| `images`      | array   | yes      | `[]`    | List of image objects already attached.             |
| `allowUpload` | boolean | no       | `false` | Whether the user can upload new photos at runtime.  |

Each image object:

| Field     | Type   | Required | Description                                            |
|-----------|--------|----------|--------------------------------------------------------|
| `imageId` | string | yes      | UUIDv7 of the stored image resource.                   |
| `url`     | string | yes      | URL to fetch the image (e.g. `/api/images/<imageId>`). |
| `caption` | string | no       | Optional descriptive caption shown below the image.    |

**Valid parents:** root checklist, section.  
**Valid children:** none (leaf node).

---

## 7. Table

**Type string:** `table`

A structured data table with typed columns and editable rows.

```json
{
  "id": "string (UUIDv7)",
  "humanReadableId": "string | null",
  "type": "table",
  "label": "string",
  "columns": [
    {
      "id": "string (UUIDv7)",
      "label": "string",
      "type": "text | number | checkbox"
    }
  ],
  "rows": [
    {
      "id": "string (UUIDv7)",
      "cells": {
        "<column-id>": "string | number | boolean"
      }
    }
  ]
}
```

`columns` — ordered list of column definitions:

| Field   | Type   | Required | Description                                                       |
|---------|--------|----------|-------------------------------------------------------------------|
| `id`    | string | yes      | UUIDv7; used as the key in each row's `cells` map.               |
| `label` | string | yes      | Column header text.                                               |
| `type`  | string | yes      | Cell type: `"text"`, `"number"`, or `"checkbox"`.                |

`rows` — list of row objects:

| Field   | Type   | Required | Description                                                       |
|---------|--------|----------|-------------------------------------------------------------------|
| `id`    | string | yes      | UUIDv7 row identifier.                                            |
| `cells` | object | yes      | Map from `column.id` → cell value. Type must match column type.  |

**Valid parents:** root checklist, section.  
**Valid children:** none (leaf node).

---

## Parent-Child Relationship Summary

| Component        | Valid parents                        | Can contain              |
|------------------|--------------------------------------|--------------------------|
| `checklist` (root) | —                                 | section, checkboxGroup, textField, numberField, imageBlock, table |
| `section`        | root, section                        | section, checkboxGroup, textField, numberField, imageBlock, table |
| `checkboxGroup`  | root, section                        | checkbox                 |
| `checkbox`       | checkboxGroup                        | —                        |
| `textField`      | root, section                        | —                        |
| `numberField`    | root, section                        | —                        |
| `imageBlock`     | root, section                        | —                        |
| `table`          | root, section                        | —                        |
