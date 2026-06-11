import { CheckboxRenderer } from './CheckboxRenderer'
import { EditableLabel } from './EditableLabel'
import styles from './CheckboxGroupRenderer.module.css'
import type { CheckboxGroupComponent } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type CheckboxGroupRendererProps = {
  component: CheckboxGroupComponent
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
}

export function CheckboxGroupRenderer({ component, isEditMode = false, onComponentUpdate }: CheckboxGroupRendererProps) {
  return (
    <section className={styles.group} data-component-id={component.id} aria-labelledby={`${component.id}-title`}>
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
          <CheckboxRenderer key={item.id} component={item} isEditMode={isEditMode} onComponentUpdate={onComponentUpdate} />
        ))}
      </div>
    </section>
  )
}
