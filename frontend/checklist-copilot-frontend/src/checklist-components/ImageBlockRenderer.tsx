import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { createPortal } from 'react-dom'
import { FiX } from 'react-icons/fi'
import { API_BASE_URL } from '../api/http'
import { deleteChecklistFile, notifyChecklistFilesChanged, uploadChecklistImageWithProgress } from '../api/files'
import { getToken } from '../auth/tokenStorage'
import { EditableLabel } from './EditableLabel'
import styles from './ImageBlockRenderer.module.css'
import type { ChecklistImage, ImageBlockComponent } from './types'
import { componentTitle, defaultLabelForType } from './utils'

const MAX_IMAGES = 3

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
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  const isSavingNewComponent = isEditMode && isTemporaryComponentId(component.id)
  const imageCount = component.images.length
  const remainingSlots = Math.max(0, MAX_IMAGES - imageCount)
  const isAtCapacity = remainingSlots === 0
  const canUpload = Boolean(
    component.allowUpload && checklistId && onComponentUpdate && !isSavingNewComponent && !isAtCapacity,
  )
  const canDeleteImages = Boolean(onComponentUpdate)
  const displayColumns = Math.min(Math.max(imageCount, 1), MAX_IMAGES)

  useEffect(() => {
    if (lightboxIndex === null) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setLightboxIndex(null)
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [lightboxIndex])

  async function handleFilesSelected(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? [])
    event.target.value = ''

    if (!selected.length || !checklistId || !onComponentUpdate) return

    const files = selected.slice(0, remainingSlots)
    const droppedCount = selected.length - files.length

    if (files.length === 0) {
      setUploadError(`This block already holds the maximum of ${MAX_IMAGES} images.`)
      return
    }

    setIsUploading(true)
    setUploadProgress(0)
    setUploadError(
      droppedCount > 0
        ? `Only ${files.length} of ${selected.length} images fit; max ${MAX_IMAGES} per block.`
        : null,
    )

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
        images: [...component.images, ...uploadedImages].slice(0, MAX_IMAGES),
      })
      notifyChecklistFilesChanged(checklistId)
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed.')
    } finally {
      setIsUploading(false)
      setUploadProgress(null)
    }
  }

  function handleDeleteImage(image: ChecklistImage) {
    const imageFileId = getImageFileId(image)
    const nextImages = component.images.filter((item) => getImageKey(item) !== getImageKey(image))

    setUploadError(null)
    onComponentUpdate?.(component.id, { images: nextImages })

    if (!imageFileId) return

    void deleteChecklistFile(imageFileId)
      .then(() => notifyChecklistFilesChanged(checklistId))
      .catch((error) => {
        setUploadError(error instanceof Error ? error.message : 'Could not delete image file.')
      })
  }

  function handleCaptionChange(image: ChecklistImage, nextCaption: string) {
    if (!onComponentUpdate) return

    const targetKey = getImageKey(image)
    const nextImages = component.images.map((item) =>
      getImageKey(item) === targetKey ? { ...item, caption: nextCaption } : item,
    )
    onComponentUpdate(component.id, { images: nextImages })
  }

  const lightboxImage = lightboxIndex !== null ? component.images[lightboxIndex] : null

  return (
    <section className={`${styles.block} ${isEditMode ? styles.editMode : ''}`} data-component-id={component.id}>
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

      {imageCount > 0 ? (
        <div
          className={styles.images}
          style={{ gridTemplateColumns: `repeat(${displayColumns}, minmax(0, 1fr))` }}
        >
          {component.images.slice(0, MAX_IMAGES).map((image, index) => {
            const imageUrl = image.url ?? image.path
            const imageLabel = image.caption ?? image.label ?? componentTitle(component)
            const fallbackCaption = image.label ?? defaultLabelForType(component.type) ?? 'Image'

            return (
              <figure className={styles.card} key={getImageKey(image)}>
                {canDeleteImages ? (
                  <button
                    className={styles.deleteImageButton}
                    type="button"
                    aria-label={`Delete ${imageLabel}`}
                    title="Delete image"
                    onClick={(event) => {
                      event.stopPropagation()
                      handleDeleteImage(image)
                    }}
                  >
                    <FiX />
                  </button>
                ) : null}
                <button
                  type="button"
                  className={styles.imageButton}
                  aria-label={`Open ${imageLabel} in full size`}
                  onClick={() => setLightboxIndex(index)}
                >
                  {imageUrl ? (
                    <AuthenticatedImage src={imageUrl} alt={imageLabel} />
                  ) : (
                    <div className={styles.placeholder}>Image</div>
                  )}
                </button>
                <figcaption className={styles.caption}>
                  <EditableLabel
                    value={imageLabel}
                    fallbackValue={fallbackCaption}
                    isEditMode={Boolean(onComponentUpdate)}
                    ariaLabel="Image caption"
                    onChange={(value) => handleCaptionChange(image, value)}
                  />
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
          <span className={styles.uploadHint}>
            {imageCount}/{MAX_IMAGES} images
          </span>
          {isUploading && uploadProgress !== null ? (
            <span className={styles.uploadStatus}>{uploadProgress}%</span>
          ) : null}
          {isSavingNewComponent ? <span className={styles.uploadHint}>Saving image block...</span> : null}
          {!checklistId ? <span className={styles.uploadHint}>Open a saved checklist to upload.</span> : null}
          {isAtCapacity && !isUploading ? (
            <span className={styles.uploadHint}>Delete an image to add another.</span>
          ) : null}
          {uploadError ? <span className={styles.uploadError}>{uploadError}</span> : null}
        </div>
      ) : null}

      {lightboxImage ? (
        <ImageLightbox
          image={lightboxImage}
          caption={lightboxImage.caption ?? lightboxImage.label ?? componentTitle(component)}
          onClose={() => setLightboxIndex(null)}
        />
      ) : null}
    </section>
  )
}

// Renders the enlarged image outside the checklist tree so fixed positioning is always viewport-relative.
// This avoids transformed or scrolled checklist containers becoming the modal's containing block.
function ImageLightbox({
  image,
  caption,
  onClose,
}: {
  image: ChecklistImage
  caption: string
  onClose: () => void
}) {
  const imageUrl = image.url ?? image.path

  return createPortal(
    <div
      className={styles.lightboxBackdrop}
      role="dialog"
      aria-modal="true"
      aria-label={caption}
      onClick={onClose}
    >
      <div className={styles.lightboxContent} onClick={(event) => event.stopPropagation()}>
        <button type="button" className={styles.lightboxClose} aria-label="Close image" onClick={onClose}>
          <FiX />
        </button>
        {imageUrl ? (
          <AuthenticatedImage src={imageUrl} alt={caption} />
        ) : (
          <div className={styles.placeholder}>Image</div>
        )}
        {caption ? <p className={styles.lightboxCaption}>{caption}</p> : null}
      </div>
    </div>,
    document.body,
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

  if (hasError) {
    return (
      <div className={`${styles.placeholder} ${styles.imageError}`} role="img" aria-label={`${alt} could not be loaded`}>
        Could not load image
      </div>
    )
  }

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

function getImageFileId(image: ChecklistImage) {
  return image.imageId ?? image.id ?? null
}

function getImageKey(image: ChecklistImage) {
  return getImageFileId(image) ?? image.url ?? image.path ?? image.caption ?? 'image'
}
