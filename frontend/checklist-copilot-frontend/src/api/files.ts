import { apiRequest } from './http'

export type FileUploadResponse = {
  id: string
  file_type: string
  file_name: string
  created_at: string
  user_id: string | null
  checklist_id: string | null
  url: string
}

export function uploadChecklistPdf(checklistId: string, file: File): Promise<FileUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('checklist_id', checklistId)

  return apiRequest<FileUploadResponse>('/files/upload/pdf', {
    method: 'POST',
    body: formData,
  })
}
