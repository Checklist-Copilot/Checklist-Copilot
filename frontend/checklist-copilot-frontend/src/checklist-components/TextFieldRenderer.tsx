import { EditableLabel } from './EditableLabel'
import styles from './TextFieldRenderer.module.css'
import type { TextFieldComponent } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type TextFieldRendererProps = {
  component: TextFieldComponent
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
}

// Renders a configurable text field and lets template editors promote typed sample text into placeholder guidance.
export function TextFieldRenderer({ component, isEditMode = false, onComponentUpdate }: TextFieldRendererProps) {
  function handleUseValueAsPlaceholder() {
    onComponentUpdate?.(component.id, {
      placeholder: component.value,
      value: '',
    })
  }

  const labelContent = (
    <>
      <EditableLabel
        value={componentTitle(component)}
        fallbackValue={defaultLabelForType(component.type)}
        isEditMode={isEditMode}
        ariaLabel="Text field label"
        onChange={(value) => onComponentUpdate?.(component.id, { label: value })}
      />
      {component.required ? <span className={styles.requiredBadge}>Required</span> : null}
    </>
  )

  return (
    <div className={`${styles.field} ${isEditMode ? styles.editMode : ''}`} data-component-id={component.id}>
      {isEditMode ? (
        <div className={styles.labelRow}>{labelContent}</div>
      ) : (
        <label className={styles.labelRow} htmlFor={component.id}>{labelContent}</label>
      )}

      {component.description ? <p className={styles.description}>{component.description}</p> : null}

      <div className={styles.inputGroup}>
        {component.multiline ? (
          <textarea
            id={component.id}
            className={styles.textarea}
            value={component.value}
            onChange={(event) => onComponentUpdate?.(component.id, { value: event.target.value })}
            placeholder={component.placeholder ?? undefined}
            required={component.required}
          />
        ) : (
          <input
            id={component.id}
            className={styles.input}
            type="text"
            value={component.value}
            onChange={(event) => onComponentUpdate?.(component.id, { value: event.target.value })}
            placeholder={component.placeholder ?? undefined}
            required={component.required}
          />
        )}

        {isEditMode ? (
          <button
            className={styles.placeholderButton}
            type="button"
            onClick={handleUseValueAsPlaceholder}
            disabled={!component.value}
          >
            Set as placeholder
          </button>
        ) : null}
      </div>
    </div>
  )
}
