import { getToken } from '../auth/tokenStorage'
import { ApiError } from './http'

// We can't use the shared `apiRequest` here because it always sets
// `Content-Type: application/json`. For multipart uploads the browser must
// set its own `multipart/form-data` Content-Type (it generates the boundary).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

export type FileUploadResponse = {
  id: string
  url: string  // ready-to-use URL the frontend can drop into an imageBlock.url
  file_type: string
  file_name: string
  user_id: string | null
  checklist_id: string | null
  created_at: string
}

async function uploadFile(
  path: string,
  file: File,
  checklistId?: string | null,
): Promise<FileUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  if (checklistId) form.append('checklist_id', checklistId)

  const headers = new Headers()
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  // Intentionally NOT setting Content-Type — browser sets it with the boundary.

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    body: form,
    headers,
  })

  const text = await response.text()
  const data = text ? JSON.parse(text) : null
  if (!response.ok) {
    const message =
      data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string'
        ? data.detail
        : response.statusText || 'Upload failed'
    throw new ApiError(message, response.status, data)
  }
  return data as FileUploadResponse
}

export function uploadImage(file: File, checklistId?: string | null) {
  return uploadFile('/files/upload/image', file, checklistId)
}

export function uploadPdf(file: File, checklistId?: string | null) {
  return uploadFile('/files/upload/pdf', file, checklistId)
}
