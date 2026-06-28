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

export type AiObserveMessage = {
  role: 'user' | 'assistant'
  content: string
}

export type AiChecklistMode = 'edit' | 'use'

export type AiObserveRequest = {
  instruction: string
  image_ids: string[]
  mode?: AiChecklistMode
  prior_messages?: AiObserveMessage[]
}

export type AiCreateFromTextRequest = {
  prompt: string
  title?: string | null
  description?: string | null
}

// Sends the user's chat text and current UI mode to the backend AI edit endpoint.
export function editChecklistWithAi(
  checklistId: string,
  instruction: string,
  mode: AiChecklistMode = 'edit',
): Promise<AiEditChecklistResponse> {
  return apiRequest<AiEditChecklistResponse>(`/ai/checklists/${checklistId}/edit`, {
    method: 'POST',
    body: JSON.stringify({ instruction, mode }),
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

// Sends uploaded image ids to the vision endpoint so the backend can inspect
// each image and optionally attach it to the best matching image block.
export function observeChecklistImages(
  checklistId: string,
  payload: AiObserveRequest,
): Promise<AiEditChecklistResponse> {
  return apiRequest<AiEditChecklistResponse>(`/ai/checklists/${checklistId}/observe`, {
    method: 'POST',
    body: JSON.stringify(payload),
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
