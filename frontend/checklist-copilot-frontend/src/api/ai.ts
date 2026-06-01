import { apiRequest } from './http'

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
