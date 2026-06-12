import { ComponentRenderer } from './ComponentRenderer'
import styles from './ChecklistRenderer.module.css'
import type { ChecklistRoot } from './types'

type ChecklistRendererProps = {
  checklist: ChecklistRoot
  checklistId?: string
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
  onDeleteComponent?: (componentId: string) => void
  focusedComponentId?: string
  onFocusComponent?: (componentId: string) => void
}

export function ChecklistRenderer({
  checklist,
  checklistId,
  isEditMode = false,
  onComponentUpdate,
  onDeleteComponent,
  focusedComponentId,
  onFocusComponent,
}: ChecklistRendererProps) {
  return (
    <div className={styles.root} data-checklist-id={checklist.id}>
      {checklist.children.map((component, index) => (
        <div
          key={component.id}
          className={`${styles.componentWrapper} ${
            focusedComponentId === component.id ? styles.focusedComponent : ''
          }`}
          onClick={(event) => {
            event.stopPropagation()
            onFocusComponent?.(component.id)
          }}
        >
          {isEditMode ? (
            <button
              type="button"
              className={styles.deleteButton}
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
            index={index}
            checklistId={checklistId}
            isEditMode={isEditMode}
            onComponentUpdate={onComponentUpdate}
            onDeleteComponent={onDeleteComponent}
            focusedComponentId={focusedComponentId}
            onFocusComponent={onFocusComponent}
          />
        </div>
      ))}
    </div>
  )
}
