import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { API_BASE_URL } from '../api/http'
import { getToken } from '../auth/tokenStorage'
import checklyLogo from '../assets/logo.svg'
import styles from './ChecklistPrintReport.module.css'
import type { ChecklistComponent, ChecklistRoot } from './types'
import { componentTitle } from './utils'

type ChecklistPrintStat = {
  label: string
  value: string | number
}

type ChecklistPrintReportProps = {
  title: string
  description?: string | null
  checklist: ChecklistRoot
  stats: ChecklistPrintStat[]
  onReady?: () => void
}

/*
16:27
ChecklistPrintReport.tsx is a reusable print/PDF component that receives a checklist, title, description, and stats, then 
renders a clean report with the logo, summary stats, and checklist content underneath. It walks through the checklist JSON and 
converts sections, checkboxes, fields, images, and tables into simple printable text with indentation and required-field labels.*/

export function ChecklistPrintReport({
  title,
  description,
  checklist,
  stats,
  onReady,
}: ChecklistPrintReportProps) {
  const imageCount = countPrintableImages(checklist)
  const [settledImageCount, setSettledImageCount] = useState(0)

  useEffect(() => {
    setSettledImageCount(0)
  }, [checklist])

  useEffect(() => {
    if (!onReady || settledImageCount < imageCount) return

    const animationFrame = window.requestAnimationFrame(() => onReady())
    return () => window.cancelAnimationFrame(animationFrame)
  }, [imageCount, onReady, settledImageCount])

  return (
    <section className={styles.report} data-print-report aria-hidden="true">
      <header className={styles.header}>
        <img src={checklyLogo} alt="Checkly logo" className={styles.logo} />
        <p className={styles.eyebrow}>Checklist Report</p>
        <h1>{title}</h1>
        <p>{description ?? 'No description.'}</p>
      </header>

      <div className={styles.stats}>
        {stats.map((stat) => (
          <div key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
          </div>
        ))}
      </div>

      <div className={styles.checklistText}>
        {checklist.children.map((component, index) => (
          <PrintChecklistComponent
            key={component.id}
            component={component}
            level={0}
            indexPath={`${index + 1}`}
            onImageSettled={() => setSettledImageCount((count) => count + 1)}
          />
        ))}
      </div>
    </section>
  )
}

function PrintChecklistComponent({
  component,
  level,
  indexPath,
  onImageSettled,
}: {
  component: ChecklistComponent
  level: number
  indexPath: string
  onImageSettled: () => void
}) {
  const title = componentTitle(component)

  if (component.type === 'section') {
    return (
      <section className={styles.section} style={{ '--print-level': level } as CSSProperties}>
        <h2 className={styles.sectionTitle}>
          {indexPath}. {title}
        </h2>
        {component.description ? <p className={styles.description}>{component.description}</p> : null}
        {component.children.map((child, index) => (
          <PrintChecklistComponent
            key={child.id}
            component={child}
            level={level + 1}
            indexPath={`${indexPath}.${index + 1}`}
            onImageSettled={onImageSettled}
          />
        ))}
      </section>
    )
  }

  if (component.type === 'checkboxGroup' || component.type === 'checkboxContainer') {
    return (
      <section className={styles.group} style={{ '--print-level': level } as CSSProperties}>
        <h3 className={styles.groupTitle}>
          {indexPath}. {title}
        </h3>
        {component.description ? <p className={styles.description}>{component.description}</p> : null}
        <ul className={styles.list}>
          {component.items.map((item) => (
            <li key={item.id}>
              {item.required ? <span className={styles.required}>Required</span> : null}
              {item.checked ? '[x]' : '[ ]'} {componentTitle(item)}
            </li>
          ))}
        </ul>
      </section>
    )
  }

  if (component.type === 'checkbox' || component.type === 'checkboxItem') {
    return (
      <p className={styles.item} style={{ '--print-level': level } as CSSProperties}>
        {component.required ? <span className={styles.required}>Required</span> : null}
        {component.checked ? '[x]' : '[ ]'} {indexPath}. {title}
      </p>
    )
  }

  if (component.type === 'textField') {
    return (
      <p className={styles.item} style={{ '--print-level': level } as CSSProperties}>
        {component.required ? <span className={styles.required}>Required</span> : null}
        {indexPath}. {title}: {component.value || 'Not filled'}
      </p>
    )
  }

  if (component.type === 'numberField' || component.type === 'numericField') {
    const value = component.value === null || component.value === undefined ? 'Not filled' : component.value

    return (
      <p className={styles.item} style={{ '--print-level': level } as CSSProperties}>
        {component.required ? <span className={styles.required}>Required</span> : null}
        {indexPath}. {title}: {value}
        {component.unit ? ` ${component.unit}` : ''}
      </p>
    )
  }

  if (component.type === 'imageBlock' || component.type === 'imagesSection') {
    return (
      <section className={`${styles.group} ${styles.imageGroup}`} style={{ '--print-level': level } as CSSProperties}>
        <h3 className={styles.groupTitle}>
          {indexPath}. {title}
        </h3>
        {component.description ? <p className={styles.description}>{component.description}</p> : null}
        {component.images.length > 0 ? (
          <div className={styles.imageGrid}>
            {component.images.map((image) => {
              const imageUrl = image.url ?? image.path
              const imageLabel = image.caption ?? image.label ?? title

              return (
                <figure className={styles.imageFigure} key={getPrintImageKey(image)}>
                  {imageUrl ? (
                    <PrintImage src={imageUrl} alt={imageLabel} onSettled={onImageSettled} />
                  ) : (
                    <div className={styles.imagePlaceholder}>Image unavailable</div>
                  )}
                  <figcaption>{imageLabel}</figcaption>
                </figure>
              )
            })}
          </div>
        ) : (
          <p className={styles.emptyImages}>No images attached.</p>
        )}
      </section>
    )
  }

  if (component.type === 'table') {
    return (
      <section className={styles.group} style={{ '--print-level': level } as CSSProperties}>
        <h3 className={styles.groupTitle}>
          {indexPath}. {title}
        </h3>
        {component.description ? <p className={styles.description}>{component.description}</p> : null}
        <table className={styles.table}>
          <thead>
            <tr>
              {component.columns.map((column) => (
                <th key={column.id}>{column.unit ? `${column.label} (${column.unit})` : column.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {component.rows.map((row) => (
              <tr key={row.id}>
                {component.columns.map((column) => (
                  <td key={column.id}>{formatPrintValue(row.cells[column.id])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    )
  }

  return null
}

function PrintImage({ src, alt, onSettled }: { src: string; alt: string; onSettled: () => void }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [hasError, setHasError] = useState(false)
  const hasSettledRef = useRef(false)

  function markSettled() {
    if (hasSettledRef.current) return
    hasSettledRef.current = true
    onSettled()
  }

  useEffect(() => {
    hasSettledRef.current = false

    if (src.startsWith('data:') || src.startsWith('blob:')) {
      setObjectUrl(src)
      return
    }

    const abortController = new AbortController()
    let currentObjectUrl: string | null = null

    async function loadImage() {
      setHasError(false)
      setObjectUrl(null)

      try {
        const token = getToken()
        const headers = new Headers()
        if (token) headers.set('Authorization', `Bearer ${token}`)

        const response = await fetch(resolvePrintImageUrl(src), {
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

  useEffect(() => {
    if (hasError) markSettled()
  }, [hasError])

  if (hasError) return <div className={styles.imagePlaceholder}>Could not load image</div>
  if (!objectUrl) return <div className={styles.imagePlaceholder}>Loading image</div>

  return <img src={objectUrl} alt={alt} onLoad={markSettled} onError={markSettled} />
}

function resolvePrintImageUrl(src: string) {
  if (/^https?:\/\//i.test(src)) return src

  const apiBaseUrl = new URL(API_BASE_URL, window.location.origin)
  if (src.startsWith('/api/')) return `${apiBaseUrl.origin}${src}`
  if (src.startsWith('/')) return `${apiBaseUrl.origin}${src}`

  return `${API_BASE_URL.replace(/\/$/, '')}/${src}`
}

function countPrintableImages(checklist: ChecklistRoot) {
  let count = 0

  function walk(component: ChecklistComponent) {
    if (component.type === 'section') {
      component.children.forEach(walk)
      return
    }

    if (component.type === 'imageBlock' || component.type === 'imagesSection') {
      count += component.images.filter((image) => image.url || image.path).length
    }
  }

  checklist.children.forEach(walk)
  return count
}

function getPrintImageKey(image: { imageId?: string; id?: string; url?: string; path?: string; caption?: string | null; label?: string | null }) {
  return image.imageId ?? image.id ?? image.url ?? image.path ?? image.caption ?? image.label ?? 'image'
}

function formatPrintValue(value: unknown) {
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}
