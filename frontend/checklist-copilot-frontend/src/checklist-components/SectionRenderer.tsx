import { ComponentRenderer } from './ComponentRenderer'
import styles from './SectionRenderer.module.css'
import type { SectionComponent } from './types'
import { componentTitle } from './utils'

type SectionRendererProps = {
  section: SectionComponent
  index?: number
  isEditMode?: boolean
  onSectionUpdate?: (sectionId: string, patch: Record<string, unknown>) => void
  onDeleteComponent?: (componentId: string) => void
  focusedComponentId?: string
  onFocusComponent?: (componentId: string) => void
}

export function SectionRenderer({
  section,
  index,
  isEditMode = false,
  onSectionUpdate,
  onDeleteComponent,
  focusedComponentId,
  onFocusComponent,
}: SectionRendererProps) {
  return (
    <section className={styles.section} data-component-id={section.id}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>
            {index !== undefined ? <span className={styles.index}>{index + 1}</span> : null}

            <input
              className={styles.titleInput}
              value={componentTitle(section)}
              onClick={(event) => event.stopPropagation()}
              onChange={(event) =>
                onSectionUpdate?.(section.id, { label: event.target.value })
              }
            />
          </h2>

          {section.description ? <p className={styles.description}>{section.description}</p> : null}
        </div>

        {section.collapsed ? <span className={styles.collapsedBadge}>Collapsed</span> : null}
      </div>

      {!section.collapsed ? (
        <div className={styles.children}>
          {section.children.map((component) => (
            <div
              key={component.id}
              className={`${styles.childWrapper} ${
                focusedComponentId === component.id ? styles.focusedChild : ''
              }`}
              onClick={(event) => {
                event.stopPropagation()
                onFocusComponent?.(component.id)
              }}
            >
              {isEditMode ? (
                <button
                  type="button"
                  className={styles.childDeleteButton}
                  aria-label="Delete component"
                  onClick={(event) => {
                    event.stopPropagation()
                    onDeleteComponent?.(component.id)
                  }}
                >
                  ×
                </button>
              ) : null}

              <ComponentRenderer
                component={component}
                isEditMode={isEditMode}
                onSectionUpdate={onSectionUpdate}
                onDeleteComponent={onDeleteComponent}
                focusedComponentId={focusedComponentId}
                onFocusComponent={onFocusComponent}
              />
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}