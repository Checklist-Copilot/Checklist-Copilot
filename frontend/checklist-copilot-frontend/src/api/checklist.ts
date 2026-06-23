import { apiRequest } from './http'
import type { Checklist, ChecklistListResponse } from '../types/checklist'

export type ChecklistCreateRequest = {
  title: string
  description?: string | null
  // The hierarchical checklist JSON. For a brand-new empty checklist the
  // frontend sends `{ id: "root", type: "root", children: [] }`.
  checklist: Record<string, unknown>
}

export function listChecklists(): Promise<ChecklistListResponse> {
  return apiRequest<ChecklistListResponse>('/checklists', { method: 'GET' })
}

export function getChecklistById(checklistId: string): Promise<Checklist> {
  return apiRequest<Checklist>(`/checklists/${checklistId}`, { method: 'GET' })
}

// POST /api/checklists/create — manual create, returns the persisted row.
export function createChecklist(payload: ChecklistCreateRequest): Promise<Checklist> {
  return apiRequest<Checklist>('/checklists/create', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// PATCH /api/checklists/{id}/metadata — update title/description only,
// without touching the JSON tree.
export function updateChecklistMetadata(
  checklistId: string,
  payload: { title?: string | null; description?: string | null },
): Promise<Checklist> {
  return apiRequest<Checklist>(`/checklists/${checklistId}/metadata`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

// DELETE /api/checklists/delete/{id} — hard delete; the row + its files
// (via CASCADE) are removed.
export function deleteChecklist(checklistId: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/checklists/delete/${checklistId}`, {
    method: 'DELETE',
  })
}

// One operation in the checklist-update protocol. Matches the discriminated
// union the backend validates (see app/schemas/checklist_operations.py).
export type AddComponentPayload = { type: string; label: string } & Record<string, unknown>

export type ChecklistOperation =
  | { operation: 'addComponent'; targetContainerId: string; position?: string | Record<string, unknown>; component: AddComponentPayload }
  | { operation: 'updateComponent'; targetId: string; patch: Record<string, unknown> }
  | { operation: 'deleteComponent'; targetId: string }

function defaultComponentLabel(type: string) {
  switch (type) {
    case 'section':
      return 'New Section'
    case 'textField':
      return 'New Text Field'
    case 'numberField':
      return 'New Number Field'
    case 'checkboxGroup':
      return 'New Checkbox Group'
    case 'checkbox':
      return 'New checkbox item'
    case 'imageBlock':
      return 'New Image Block'
    case 'table':
      return 'New Table'
    default:
      return 'New Component'
  }
}

function toApiOperation(operation: ChecklistOperation): ChecklistOperation {
  if (operation.operation !== 'addComponent') return operation

  const type = String(operation.component.type)
  const rawLabel = operation.component.label
  const label = typeof rawLabel === 'string' && rawLabel.trim() ? rawLabel : defaultComponentLabel(type)
  const component: AddComponentPayload = { type, label }

  if (type === 'imageBlock') {
    const images = operation.component.images
    const allowUpload = operation.component.allowUpload

    if (Array.isArray(images)) component.images = images
    if (typeof allowUpload === 'boolean') component.allowUpload = allowUpload
  }

  // The backend owns generated ids/default structure for new components, but
  // add handlers require a real label. Preserve imageBlock upload settings so
  // the server response does not turn off uploads after the optimistic render.
  return {
    ...operation,
    component,
  }
}

// PATCH /api/checklists/{id} — apply a batch of operations to the tree.
// The backend validates each one, applies them, snapshots `checklist_prev`,
// recomputes stats, and returns the persisted row.
export function updateChecklistById(
  checklistId: string,
  operations: ChecklistOperation[],
): Promise<Checklist> {
  return apiRequest<Checklist>(`/checklists/${checklistId}`, {
    method: 'PATCH',
    body: JSON.stringify({ operations: operations.map(toApiOperation) }),
  })
}

export function restorePreviousChecklist(checklistId: string): Promise<Checklist> {
  return apiRequest<Checklist>(`/checklists/${checklistId}/restore-previous`, {
    method: 'POST',
  })
}

export function restoreChecklistJson(
  checklistId: string,
  checklist: Record<string, unknown>,
): Promise<Checklist> {
  return apiRequest<Checklist>(`/checklists/${checklistId}/restore-json`, {
    method: 'POST',
    body: JSON.stringify({ checklist }),
  })
}
