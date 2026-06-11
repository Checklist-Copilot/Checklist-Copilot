import { ComponentRenderer } from './ComponentRenderer'
import { EditableLabel } from './EditableLabel'
import styles from './SectionRenderer.module.css'
import type { SectionComponent } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type SectionRendererProps = {
  section: SectionComponent
  index?: number
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
  onDeleteComponent?: (componentId: string) => void
  focusedComponentId?: string
  onFocusComponent?: (componentId: string) => void
}

export function SectionRenderer({
  section,
  index,
  isEditMode = false,
  onComponentUpdate,
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

            <EditableLabel
              value={componentTitle(section)}
              fallbackValue={defaultLabelForType(section.type)}
              isEditMode={isEditMode}
              ariaLabel="Section label"
              onChange={(value) => onComponentUpdate?.(section.id, { label: value })}
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
                onComponentUpdate={onComponentUpdate}
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