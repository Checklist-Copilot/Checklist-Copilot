import { apiRequest } from './http'
import type { Checklist, ChecklistListResponse } from '../types/checklist'

export function listChecklists(): Promise<ChecklistListResponse> {
  return apiRequest<ChecklistListResponse>('/checklists', { method: 'GET' })
}

export function getChecklistById(checklistId: string): Promise<Checklist> {
  return apiRequest<Checklist>(`/checklists/${checklistId}`, { method: 'GET' })
}
