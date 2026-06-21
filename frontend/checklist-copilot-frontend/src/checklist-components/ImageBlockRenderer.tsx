import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { API_BASE_URL } from '../api/http'
import { uploadChecklistImageWithProgress } from '../api/files'
import { getToken } from '../auth/tokenStorage'
import { EditableLabel } from './EditableLabel'
import styles from './ImageBlockRenderer.module.css'
import type { ChecklistImage, ImageBlockComponent } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type ImageBlockRendererProps = {
  component: ImageBlockComponent
  checklistId?: string
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
}

export function ImageBlockRenderer({
  component,
  checklistId,
  isEditMode = false,
  onComponentUpdate,
}: ImageBlockRendererProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const isSavingNewComponent = isEditMode && isTemporaryComponentId(component.id)
  const canUpload = Boolean(component.allowUpload && checklistId && onComponentUpdate && !isSavingNewComponent)

  async function handleFilesSelected(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''

    if (!files.length || !checklistId || !onComponentUpdate) return

    setIsUploading(true)
    setUploadProgress(0)
    setUploadError(null)

    try {
      const uploadedImages: ChecklistImage[] = []

      for (const file of files) {
        const response = await uploadChecklistImageWithProgress(checklistId, file, setUploadProgress)

        uploadedImages.push({
          imageId: response.id,
          url: response.url,
          caption: response.title ?? response.file_name,
        })
      }

      onComponentUpdate(component.id, {
        images: [...component.images, ...uploadedImages],
      })
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed.')
    } finally {
      setIsUploading(false)
      setUploadProgress(null)
    }
  }

  return (
    <section className={styles.block} data-component-id={component.id}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>
            <EditableLabel
              value={componentTitle(component)}
              fallbackValue={defaultLabelForType(component.type)}
              isEditMode={isEditMode}
              ariaLabel="Image block label"
              onChange={(value) => onComponentUpdate?.(component.id, { label: value })}
            />
          </h3>
          {component.description ? <p className={styles.description}>{component.description}</p> : null}
        </div>
        {component.allowUpload ? <span className={styles.uploadBadge}>Upload enabled</span> : null}
      </div>

      {component.images.length > 0 ? (
        <div className={styles.images}>
          {component.images.map((image) => {
            const imageUrl = image.url ?? image.path
            const imageLabel = image.caption ?? image.label ?? componentTitle(component)

            return (
              <figure className={styles.card} key={image.imageId ?? image.id ?? image.path}>
                {imageUrl ? (
                  <AuthenticatedImage src={imageUrl} alt={imageLabel} />
                ) : (
                  <div className={styles.placeholder}>Image</div>
                )}
                <figcaption className={styles.caption}>
                  {imageLabel}
                  {image.bucket || image.mimeType ? (
                    <span className={styles.meta}>{[image.bucket, image.mimeType].filter(Boolean).join(' · ')}</span>
                  ) : null}
                </figcaption>
              </figure>
            )
          })}
        </div>
      ) : (
        <p className={styles.emptyText}>No images attached.</p>
      )}

      {component.allowUpload ? (
        <div className={styles.uploadControls}>
          <input
            ref={fileInputRef}
            className={styles.fileInput}
            type="file"
            accept="image/png,image/jpeg"
            multiple
            onChange={handleFilesSelected}
          />
          <button
            className={styles.uploadButton}
            type="button"
            disabled={!canUpload || isUploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {isUploading ? 'Uploading...' : 'Upload photo'}
          </button>
          {isUploading && uploadProgress !== null ? (
            <span className={styles.uploadStatus}>{uploadProgress}%</span>
          ) : null}
          {isSavingNewComponent ? <span className={styles.uploadHint}>Saving image block...</span> : null}
          {!checklistId ? <span className={styles.uploadHint}>Open a saved checklist to upload.</span> : null}
          {uploadError ? <span className={styles.uploadError}>{uploadError}</span> : null}
        </div>
      ) : null}
    </section>
  )
}

function AuthenticatedImage({ src, alt }: { src: string; alt: string }) {
  if (src.startsWith('data:') || src.startsWith('blob:')) return <img src={src} alt={alt} />

  return <FetchedImage src={src} alt={alt} />
}

function FetchedImage({ src, alt }: { src: string; alt: string }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    const abortController = new AbortController()
    let currentObjectUrl: string | null = null

    async function loadImage() {
      setHasError(false)
      setObjectUrl(null)

      try {
        const token = getToken()
        const headers = new Headers()
        if (token) headers.set('Authorization', `Bearer ${token}`)

        const response = await fetch(resolveImageUrl(src), {
          headers,
          signal: abortController.signal,
        })

        if (!response.ok) throw new Error('Image request failed')

        const blob = await response.blob()
        currentObjectUrl = URL.createObjectURL(blob)
        setObjectUrl(currentObjectUrl)
      } catch {
        if (!abortController.signal.aborted) setHasError(true)
      }
    }

    void loadImage()

    return () => {
      abortController.abort()
      if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl)
    }
  }, [src])

  if (hasError) return <div className={styles.placeholder}>Image unavailable</div>
  if (!objectUrl) return <div className={styles.placeholder}>Loading image</div>

  return <img src={objectUrl} alt={alt} />
}

function resolveImageUrl(src: string) {
  if (/^https?:\/\//i.test(src)) return src

  const apiBaseUrl = new URL(API_BASE_URL, window.location.origin)
  if (src.startsWith('/api/')) return `${apiBaseUrl.origin}${src}`
  if (src.startsWith('/')) return `${apiBaseUrl.origin}${src}`

  return `${API_BASE_URL.replace(/\/$/, '')}/${src}`
}

function isTemporaryComponentId(componentId: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(componentId)
}
