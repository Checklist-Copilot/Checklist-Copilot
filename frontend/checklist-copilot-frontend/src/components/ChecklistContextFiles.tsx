import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { createPortal } from 'react-dom'
import { FiEye, FiFileText, FiImage, FiRefreshCw, FiTrash2, FiUpload, FiX } from 'react-icons/fi'
import { getToken } from '../auth/tokenStorage'
import { API_BASE_URL } from '../api/http'
import {
  deleteChecklistFile,
  listChecklistFiles,
  uploadChecklistFileWithProgress,
  type ChecklistContextFile,
} from '../api/files'
import styles from '../components-styles/ChecklistContextFiles.module.css'

type UploadState = {
  fileName: string
  progress: number
  status: 'uploading' | 'error'
  error?: string
}

type ChecklistContextFilesProps = {
  checklistId?: string
}

type PreviewState = {
  file: ChecklistContextFile
  objectUrl: string | null
  status: 'loading' | 'ready' | 'error'
  error?: string
}

type FileTypeFilter = 'all' | 'pdf' | 'image'

const MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024
const MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024

function getUploadFileType(file: File): 'pdf' | 'image' | null {
  if (file.type === 'application/pdf') return 'pdf'
  if (file.type === 'image/png' || file.type === 'image/jpeg') return 'image'
  return null
}

function getUploadSizeLimit(fileType: 'pdf' | 'image') {
  return fileType === 'pdf' ? MAX_PDF_SIZE_BYTES : MAX_IMAGE_SIZE_BYTES
}

function resolveApiUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path
  if (path.startsWith('/api/')) return `${API_BASE_URL.replace(/\/api\/?$/, '')}${path}`
  return `${API_BASE_URL}${path}`
}

function displayFileName(file: ChecklistContextFile) {
  if (file.title) return file.title

  const parts = file.file_name.split('/')
  return parts[parts.length - 1] || file.file_name
}

export function ChecklistContextFiles({ checklistId }: ChecklistContextFilesProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [files, setFiles] = useState<ChecklistContextFile[]>([])
  const [previewUrls, setPreviewUrls] = useState<Record<string, string>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [uploadState, setUploadState] = useState<UploadState | null>(null)
  const [deletingFileId, setDeletingFileId] = useState<string | null>(null)
  const [previewState, setPreviewState] = useState<PreviewState | null>(null)
  const [previewLoadingFileId, setPreviewLoadingFileId] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<FileTypeFilter>('all')

  const counts = useMemo(
    () => ({
      all: files.length,
      pdfs: files.filter((file) => file.file_type === 'pdf').length,
      images: files.filter((file) => file.file_type === 'image').length,
    }),
    [files],
  )

  const filteredFiles = useMemo(() => {
    if (activeFilter === 'all') return files
    return files.filter((file) => file.file_type === activeFilter)
  }, [activeFilter, files])

  const refreshFiles = useCallback(async () => {
    if (!checklistId) return

    setIsLoading(true)
    setErrorMessage(null)

    try {
      const response = await listChecklistFiles(checklistId)
      setFiles(response.files)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Could not load context files.')
    } finally {
      setIsLoading(false)
    }
  }, [checklistId])

  async function handleFilesSelected(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? [])
    event.target.value = ''

    if (!checklistId || selectedFiles.length === 0) return

    for (const file of selectedFiles) {
      setUploadState({ fileName: file.name, progress: 0, status: 'uploading' })

      try {
        const fileType = getUploadFileType(file)
        if (!fileType) throw new Error('Only PDF, PNG, and JPEG files are allowed.')
        if (file.size > getUploadSizeLimit(fileType)) {
          throw new Error(fileType === 'pdf' ? 'PDF files must be 10 MB or smaller.' : 'Images must be 2 MB or smaller.')
        }

        const uploaded = await uploadChecklistFileWithProgress(checklistId, file, fileType, (progress) => {
          setUploadState({ fileName: file.name, progress, status: 'uploading' })
        })
        setFiles((currentFiles) => [
          {
            id: uploaded.id,
            file_type: uploaded.file_type,
            file_name: uploaded.file_name,
            title: uploaded.title,
            created_at: uploaded.created_at,
            user_id: uploaded.user_id,
            checklist_id: uploaded.checklist_id,
            raw_url: uploaded.url,
          },
          ...currentFiles,
        ])
        setUploadState(null)
      } catch (error) {
        setUploadState({
          fileName: file.name,
          progress: 0,
          status: 'error',
          error: error instanceof Error ? error.message : 'Upload failed.',
        })
        break
      }
    }
  }

  async function handleDelete(fileId: string) {
    setDeletingFileId(fileId)
    setErrorMessage(null)

    try {
      await deleteChecklistFile(fileId)
      setFiles((currentFiles) => currentFiles.filter((file) => file.id !== fileId))
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Could not delete file.')
    } finally {
      setDeletingFileId(null)
    }
  }

  function closePreview() {
    setPreviewState((currentPreview) => {
      if (currentPreview?.objectUrl) URL.revokeObjectURL(currentPreview.objectUrl)
      return null
    })
  }

  async function handleOpenFile(file: ChecklistContextFile) {
    setErrorMessage(null)
    setPreviewLoadingFileId(file.id)
    setPreviewState((currentPreview) => {
      if (currentPreview?.objectUrl) URL.revokeObjectURL(currentPreview.objectUrl)
      return { file, objectUrl: null, status: 'loading' }
    })

    try {
      const token = getToken()
      const response = await fetch(resolveApiUrl(file.raw_url), {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      })

      if (!response.ok) throw new Error('Could not open file.')

      const blobUrl = URL.createObjectURL(await response.blob())
      setPreviewState((currentPreview) => {
        if (currentPreview?.objectUrl) URL.revokeObjectURL(currentPreview.objectUrl)
        return { file, objectUrl: blobUrl, status: 'ready' }
      })
    } catch (error) {
      setPreviewState((currentPreview) => ({
        file,
        objectUrl: currentPreview?.file.id === file.id ? currentPreview.objectUrl : null,
        status: 'error',
        error: error instanceof Error ? error.message : 'Could not open file.',
      }))
      setErrorMessage(error instanceof Error ? error.message : 'Could not open file.')
    } finally {
      setPreviewLoadingFileId(null)
    }
  }

  useEffect(() => {
    void refreshFiles()
  }, [refreshFiles])

  useEffect(() => {
    return () => {
      if (previewState?.objectUrl) URL.revokeObjectURL(previewState.objectUrl)
    }
  }, [previewState])

  useEffect(() => {
    if (!previewState) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') closePreview()
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [previewState])

  useEffect(() => {
    let isMounted = true
    const objectUrls: string[] = []

    async function loadImagePreviews() {
      const imageFiles = files.filter((file) => file.file_type === 'image')
      const loadedPreviews: Record<string, string> = {}

      await Promise.all(
        imageFiles.map(async (file) => {
          try {
            const token = getToken()
            const response = await fetch(resolveApiUrl(file.raw_url), {
              headers: token ? { Authorization: `Bearer ${token}` } : undefined,
            })
            if (!response.ok) return

            const objectUrl = URL.createObjectURL(await response.blob())
            objectUrls.push(objectUrl)
            loadedPreviews[file.id] = objectUrl
          } catch {
            loadedPreviews[file.id] = ''
          }
        }),
      )

      if (isMounted) setPreviewUrls(loadedPreviews)
    }

    void loadImagePreviews()

    return () => {
      isMounted = false
      objectUrls.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [files])

  const previewDialog = previewState
    ? createPortal(
        <div
          className={styles.previewOverlay}
          role="dialog"
          aria-modal="true"
          aria-label={displayFileName(previewState.file)}
          onMouseDown={closePreview}
        >
          <div className={styles.previewDialog} onMouseDown={(event) => event.stopPropagation()}>
            <header className={styles.previewHeader}>
              <div className={styles.previewTitleBlock}>
                <span className={styles.previewTitle}>{displayFileName(previewState.file)}</span>
                <span className={styles.previewMeta}>{previewState.file.file_type.toUpperCase()}</span>
              </div>
              <button className={styles.previewCloseButton} type="button" onClick={closePreview} aria-label="Close preview">
                <FiX />
              </button>
            </header>

            <div
              className={
                previewState.file.file_type === 'image'
                  ? `${styles.previewBody} ${styles.previewImageBody}`
                  : styles.previewBody
              }
            >
              {previewState.status === 'loading' ? <div className={styles.previewLoading}>Loading preview...</div> : null}
              {previewState.status === 'error' ? (
                <div className={styles.previewError}>{previewState.error ?? 'Could not open file.'}</div>
              ) : null}
              {previewState.status === 'ready' && previewState.objectUrl && previewState.file.file_type === 'image' ? (
                <img className={styles.previewImage} src={previewState.objectUrl} alt={displayFileName(previewState.file)} />
              ) : null}
              {previewState.status === 'ready' && previewState.objectUrl && previewState.file.file_type !== 'image' ? (
                <iframe className={styles.previewFrame} src={previewState.objectUrl} title={displayFileName(previewState.file)} />
              ) : null}
            </div>
          </div>
        </div>,
        document.body,
      )
    : null

  return (
    <>
      <section className={styles.panel} aria-labelledby="context-files-title">
        <div className={styles.header}>
          <div>
            <p className={styles.eyebrow}>AI Context</p>
            <h2 id="context-files-title" className={styles.title}>Context files</h2>
          </div>

          <div className={styles.actions}>
            <button className={styles.iconButton} type="button" onClick={refreshFiles} disabled={!checklistId || isLoading}>
              <FiRefreshCw />
              <span>Refresh</span>
            </button>
            <button className={styles.uploadButton} type="button" onClick={() => inputRef.current?.click()} disabled={!checklistId}>
              <FiUpload />
              <span>Upload files</span>
            </button>
            <input
              ref={inputRef}
              className={styles.hiddenInput}
              type="file"
              accept="application/pdf,.pdf,image/png,image/jpeg,.png,.jpg,.jpeg"
              multiple
              onChange={handleFilesSelected}
            />
          </div>
        </div>

        <div className={styles.filterRow} aria-label="Filter context files by type">
          <button
            className={`${styles.filterButton} ${activeFilter === 'all' ? styles.activeFilterButton : ''}`}
            type="button"
            onClick={() => setActiveFilter('all')}
          >
            <span>{counts.all}</span>
            All
          </button>
          <button
            className={`${styles.filterButton} ${activeFilter === 'pdf' ? styles.activeFilterButton : ''}`}
            type="button"
            onClick={() => setActiveFilter('pdf')}
          >
            <span>{counts.pdfs}</span>
            PDFs
          </button>
          <button
            className={`${styles.filterButton} ${activeFilter === 'image' ? styles.activeFilterButton : ''}`}
            type="button"
            onClick={() => setActiveFilter('image')}
          >
            <span>{counts.images}</span>
            Images
          </button>
        </div>

        {uploadState ? (
          <div className={uploadState.status === 'error' ? styles.uploadError : styles.uploadProgress} role="status">
            <span>{uploadState.fileName}</span>
            {uploadState.status === 'uploading' ? (
              <span className={styles.progressTrack}>
                <span className={styles.progressFill} style={{ width: `${uploadState.progress}%` }} />
              </span>
            ) : (
              <span>{uploadState.error}</span>
            )}
          </div>
        ) : null}

        {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
        {isLoading ? <p className={styles.message}>Loading context files...</p> : null}

        {!isLoading && files.length === 0 ? (
          <p className={styles.empty}>No context files attached yet.</p>
        ) : !isLoading && filteredFiles.length === 0 ? (
          <p className={styles.empty}>No files match this filter.</p>
        ) : (
          <ul className={styles.fileList}>
            {filteredFiles.map((file) => (
              <li key={file.id} className={styles.fileItem}>
                <div className={styles.filePreview} aria-hidden="true">
                  {file.file_type === 'image' && previewUrls[file.id] ? (
                    <img src={previewUrls[file.id]} alt="" />
                  ) : file.file_type === 'image' ? (
                    <FiImage />
                  ) : (
                    <FiFileText />
                  )}
                </div>

                <div className={styles.fileInfo}>
                  <span className={styles.fileName}>{displayFileName(file)}</span>
                  <span className={styles.fileMeta}>
                    {file.file_type.toUpperCase()} · {formatDate(file.created_at)}
                  </span>
                </div>

                <div className={styles.fileActions}>
                  <button
                    className={styles.iconOnlyButton}
                    type="button"
                    onClick={() => handleOpenFile(file)}
                    disabled={previewLoadingFileId === file.id}
                    title="Preview file"
                  >
                    <FiEye />
                  </button>
                  <button
                    className={styles.dangerButton}
                    type="button"
                    onClick={() => handleDelete(file.id)}
                    disabled={deletingFileId === file.id}
                    title="Delete file"
                  >
                    <FiTrash2 />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {previewDialog}
    </>
  )
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}
