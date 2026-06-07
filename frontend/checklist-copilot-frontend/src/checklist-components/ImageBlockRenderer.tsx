import styles from './ImageBlockRenderer.module.css'
import type { ImageBlockComponent } from './types'
import { componentTitle } from './utils'

export function ImageBlockRenderer({ component }: { component: ImageBlockComponent }) {
  // Defensive default — older rows (or AI-generated trees that skipped the
  // field) can arrive without `images`. Crashing the whole page over a missing
  // optional array isn't worth it.
  const images = component.images ?? []
  return (
    <section className={styles.block} data-component-id={component.id}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>{componentTitle(component)}</h3>
          {component.description ? <p className={styles.description}>{component.description}</p> : null}
        </div>
        {component.allowUpload ? <span className={styles.uploadBadge}>Upload enabled</span> : null}
      </div>

      {images.length > 0 ? (
        <div className={styles.images}>
          {images.map((image) => {
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
