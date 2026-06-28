import { CheckboxRenderer } from './CheckboxRenderer'
import { EditableLabel } from './EditableLabel'
import { FiX } from 'react-icons/fi'
import styles from './CheckboxGroupRenderer.module.css'
import type { CheckboxGroupComponent } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type CheckboxGroupRendererProps = {
  component: CheckboxGroupComponent
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
  onDeleteComponent?: (componentId: string) => void
  focusedComponentId?: string
  onFocusComponent?: (componentId: string) => void
}

export function CheckboxGroupRenderer({
  component,
  isEditMode = false,
  onComponentUpdate,
  onDeleteComponent,
  focusedComponentId,
  onFocusComponent,
}: CheckboxGroupRendererProps) {
  return (
    <section className={`${styles.group} ${isEditMode ? styles.editMode : ''}`} data-component-id={component.id} aria-labelledby={`${component.id}-title`}>
      <div className={styles.header}>
        <h3 className={styles.title} id={`${component.id}-title`}>
          <EditableLabel
            value={componentTitle(component)}
            fallbackValue={defaultLabelForType(component.type)}
            isEditMode={isEditMode}
            ariaLabel="Checkbox group label"
            onChange={(value) => onComponentUpdate?.(component.id, { label: value })}
          />
        </h3>
        {component.description ? <p className={styles.description}>{component.description}</p> : null}
      </div>

      <div className={styles.list}>
        {component.items.map((item) => (
          <div
            className={`${styles.itemWrapper} ${focusedComponentId === item.id ? styles.focusedItem : ''}`}
            key={item.id}
            onClick={(event) => {
              event.stopPropagation()
              onFocusComponent?.(item.id)
            }}
          >
            <CheckboxRenderer component={item} isEditMode={isEditMode} onComponentUpdate={onComponentUpdate} />
            {isEditMode ? (
              <button
                className={styles.deleteItemButton}
                type="button"
                aria-label={`Delete ${componentTitle(item)}`}
                title="Delete checkbox item"
                onClick={(event) => {
                  event.stopPropagation()
                  onDeleteComponent?.(item.id)
                }}
              >
                <FiX />
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  )
}
