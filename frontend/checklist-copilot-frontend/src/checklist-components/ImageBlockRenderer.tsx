import { EditableLabel } from './EditableLabel'
import styles from './ImageBlockRenderer.module.css'
import type { ImageBlockComponent } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type ImageBlockRendererProps = {
  component: ImageBlockComponent
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
}

export function ImageBlockRenderer({ component, isEditMode = false, onComponentUpdate }: ImageBlockRendererProps) {
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
                {imageUrl ? <img src={imageUrl} alt={imageLabel} /> : <div className={styles.placeholder}>Image</div>}
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
        <button className={styles.uploadButton} type="button" disabled>
          Upload photo
        </button>
      ) : null}
    </section>
  )
}
