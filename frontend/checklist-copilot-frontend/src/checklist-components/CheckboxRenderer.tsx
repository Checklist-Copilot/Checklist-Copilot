import { EditableLabel } from './EditableLabel'
import styles from './CheckboxRenderer.module.css'
import type { CheckboxComponent } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type CheckboxRendererProps = {
  component: CheckboxComponent
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
}

export function CheckboxRenderer({ component, isEditMode = false, onComponentUpdate }: CheckboxRendererProps) {
  const content = (
    <>
      <input
        className={styles.checkboxInput}
        type="checkbox"
        checked={component.checked}
        required={component.required}
        onChange={(event) => onComponentUpdate?.(component.id, { checked: event.target.checked })}
      />
      <span>
        <EditableLabel
          value={componentTitle(component)}
          fallbackValue={defaultLabelForType(component.type)}
          isEditMode={isEditMode}
          ariaLabel="Checkbox label"
          onChange={(value) => onComponentUpdate?.(component.id, { label: value })}
        />
      </span>
      {component.required ? <span className={styles.requiredBadge}>Required</span> : null}
    </>
  )

  if (isEditMode) {
    return (
      <div className={styles.item} data-component-id={component.id}>
        {content}
      </div>
    )
  }

  return (
    <label className={styles.item} data-component-id={component.id}>
      {content}
    </label>
  )
}
