import { apiRequest } from './http'
import type { Checklist } from '../types/checklist'

// This matches the backend response from POST /api/ai/checklists/{id}/edit.
// The backend sends back both Checkly's text reply and the updated checklist JSON.
export type AiEditChecklistResponse = {
  checklist: Record<string, unknown>
  reply: string
  applied_calls: number
  skipped: Array<{
    call: Record<string, unknown>
    reason: string
  }>
}

export type AiReviewResponse = {
  reply: string
}

export type AiCreateFromTextRequest = {
  prompt: string
  title?: string | null
  description?: string | null
}

// Sends the user's chat text to the backend as an AI edit instruction.
export function editChecklistWithAi(
  checklistId: string,
  instruction: string,
): Promise<AiEditChecklistResponse> {
  return apiRequest<AiEditChecklistResponse>(`/ai/checklists/${checklistId}/edit`, {
    method: 'POST',
    body: JSON.stringify({ instruction }),
  })
}

// POST /api/ai/checklists/create-from-text — backend generates the checklist
// tree from the natural-language prompt and persists it as a new row.
export function createChecklistFromText(
  payload: AiCreateFromTextRequest,
): Promise<Checklist> {
  return apiRequest<Checklist>('/ai/checklists/create-from-text', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// Requests an AI quality review of the checklist using linked PDFs as context.
export function reviewChecklistWithAi(checklistId: string): Promise<AiReviewResponse> {
  return apiRequest<AiReviewResponse>(`/ai/checklists/${checklistId}/review`, {
    method: 'POST',
  })
}

// POST /api/ai/checklists/{id}/generate — generates content for an existing
// empty checklist using the prompt plus any uploaded PDFs as context.
export function generateChecklistWithContext(
  checklistId: string,
  prompt: string,
): Promise<Checklist> {
  return apiRequest<Checklist>(`/ai/checklists/${checklistId}/generate`, {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}
