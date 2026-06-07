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
export type ChecklistOperation =
  | { operation: 'addComponent'; targetContainerId: string; position?: string | Record<string, unknown>; component: Record<string, unknown> }
  | { operation: 'updateComponent'; targetId: string; patch: Record<string, unknown> }
  | { operation: 'deleteComponent'; targetId: string }

// PATCH /api/checklists/{id} — apply a batch of operations to the tree.
// The backend validates each one, applies them, snapshots `checklist_prev`,
// recomputes stats, and returns the persisted row.
export function patchChecklist(
  checklistId: string,
  operations: ChecklistOperation[],
): Promise<Checklist> {
  return apiRequest<Checklist>(`/checklists/${checklistId}`, {
    method: 'PATCH',
    body: JSON.stringify({ operations }),
  })
}
