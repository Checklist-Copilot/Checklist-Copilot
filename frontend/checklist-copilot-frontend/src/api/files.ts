import { getToken } from '../auth/tokenStorage'
import { API_BASE_URL, apiRequest } from './http'

export type FileUploadResponse = {
  id: string
  file_type: string
  file_name: string
  title: string | null
  created_at: string
  user_id: string | null
  checklist_id: string | null
  url: string
}

export type ChecklistContextFile = {
  id: string
  file_type: 'pdf' | 'image' | string
  file_name: string
  title: string | null
  created_at: string
  user_id: string | null
  checklist_id: string | null
  raw_url: string
}

export type ChecklistFilesResponse = {
  files: ChecklistContextFile[]
}

export type FileDeleteResponse = {
  message: string
}

export type UploadProgressCallback = (progress: number) => void

export const CHECKLIST_FILES_CHANGED_EVENT = 'checklist-files-changed'

export function notifyChecklistFilesChanged(checklistId?: string | null, deletedFileId?: string) {
  if (!checklistId) return

  window.dispatchEvent(
    new CustomEvent(CHECKLIST_FILES_CHANGED_EVENT, {
      detail: { checklistId, deletedFileId },
    }),
  )
}

export function listChecklistFiles(
  checklistId: string,
  fileType?: 'pdf' | 'image',
): Promise<ChecklistFilesResponse> {
  const params = new URLSearchParams({ checklist_id: checklistId })
  if (fileType) params.set('file_type', fileType)

  return apiRequest<ChecklistFilesResponse>(`/files?${params.toString()}`)
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

// Uploads one camera/gallery image for AI observation or image-block attachment.
export function uploadChecklistImage(checklistId: string, file: File): Promise<FileUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('checklist_id', checklistId)

  return apiRequest<FileUploadResponse>('/files/upload/image', {
    method: 'POST',
    body: formData,
  })
}

export function uploadChecklistPdfWithProgress(
  checklistId: string,
  file: File,
  onProgress: UploadProgressCallback,
): Promise<FileUploadResponse> {
  return uploadChecklistFileWithProgress(checklistId, file, 'pdf', onProgress)
}

export function uploadChecklistImageWithProgress(
  checklistId: string,
  file: File,
  onProgress: UploadProgressCallback,
): Promise<FileUploadResponse> {
  return uploadChecklistFileWithProgress(checklistId, file, 'image', onProgress)
}

export function uploadChecklistFileWithProgress(
  checklistId: string,
  file: File,
  fileType: 'pdf' | 'image',
  onProgress: UploadProgressCallback,
): Promise<FileUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('checklist_id', checklistId)

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('POST', `${API_BASE_URL}/files/upload/${fileType}`)

    const token = getToken()
    if (token) request.setRequestHeader('Authorization', `Bearer ${token}`)

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      onProgress(Math.round((event.loaded / event.total) * 100))
    }

    request.onload = () => {
      const data = request.responseText ? JSON.parse(request.responseText) : null

      if (request.status < 200 || request.status >= 300) {
        const message =
          data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string'
            ? data.detail
            : request.statusText || 'Upload failed'
        reject(new Error(message))
        return
      }

      onProgress(100)
      resolve(data as FileUploadResponse)
    }

    request.onerror = () => reject(new Error('Upload failed'))
    request.onabort = () => reject(new Error('Upload cancelled'))
    request.send(formData)
  })
}

export function deleteChecklistFile(fileId: string): Promise<FileDeleteResponse> {
  return apiRequest<FileDeleteResponse>(`/files/delete_file/${fileId}`, {
    method: 'DELETE',
  })
}
