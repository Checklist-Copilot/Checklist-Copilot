import { ComponentRenderer } from './ComponentRenderer'
import styles from './ChecklistRenderer.module.css'
import type { ChecklistRoot } from './types'

type ChecklistRendererProps = {
  checklist: ChecklistRoot
  isEditMode?: boolean
  onDeleteComponent?: (componentId: string) => void
}

export function ChecklistRenderer({
  checklist,
  isEditMode = false,
  onDeleteComponent,
}: ChecklistRendererProps) {
  return (
    <div className={styles.root} data-checklist-id={checklist.id}>
      {checklist.children.map((component, index) => (
        <div key={component.id} className={styles.componentWrapper}>
          {isEditMode ? (
            <button
              type="button"
              className={styles.deleteButton}
              aria-label="Delete component"
              onClick={() => onDeleteComponent?.(component.id)}
            >
              ×
            </button>
          ) : null}

          <ComponentRenderer component={component} index={index} />
        </div>
      ))}
    </div>
  )
}