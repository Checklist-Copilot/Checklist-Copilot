import { EditableLabel } from './EditableLabel'
import styles from './NumberFieldRenderer.module.css'
import type { NumberFieldComponent } from './types'
import { componentTitle, defaultLabelForType, formatRange } from './utils'

type NumberFieldRendererProps = {
  component: NumberFieldComponent
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
}

export function NumberFieldRenderer({ component, isEditMode = false, onComponentUpdate }: NumberFieldRendererProps) {
  function updateValue(value: number | null) {
    onComponentUpdate?.(component.id, { value })
  }

  function stepValue(direction: -1 | 1) {
    const baseValue = component.value ?? 0
    const nextValue = baseValue + direction
    const min = component.min ?? -Infinity
    const max = component.max ?? Infinity
    updateValue(Math.min(max, Math.max(min, nextValue)))
  }

  const labelContent = (
    <>
      <EditableLabel
        value={componentTitle(component)}
        fallbackValue={defaultLabelForType(component.type)}
        isEditMode={isEditMode}
        ariaLabel="Number field label"
        onChange={(value) => onComponentUpdate?.(component.id, { label: value })}
      />
      {component.required ? <span className={styles.requiredBadge}>Required</span> : null}
    </>
  )

  return (
    <div className={styles.field} data-component-id={component.id}>
      {isEditMode ? (
        <div className={styles.labelRow}>{labelContent}</div>
      ) : (
        <label className={styles.labelRow} htmlFor={component.id}>{labelContent}</label>
      )}

      {component.description ? <p className={styles.description}>{component.description}</p> : null}

      <div className={styles.inputGrid}>
        <div className={styles.numberControl}>
          <input
            id={component.id}
            className={styles.input}
            type="number"
            value={component.value ?? ''}
            onChange={(event) => updateValue(event.target.value === '' ? null : Number(event.target.value))}
            min={component.min ?? undefined}
            max={component.max ?? undefined}
            required={component.required}
          />

          <div className={styles.stepper} aria-label="Number controls">
            <button
              type="button"
              className={styles.stepButton}
              aria-label="Increase value"
              onClick={() => stepValue(1)}
              disabled={component.max !== null && component.max !== undefined && component.value === component.max}
            >
              +
            </button>
            <button
              type="button"
              className={styles.stepButton}
              aria-label="Decrease value"
              onClick={() => stepValue(-1)}
              disabled={component.min !== null && component.min !== undefined && component.value === component.min}
            >
              −
            </button>
          </div>
        </div>

        {isEditMode ? (
          <label className={styles.unitField}>
            <span>Unit</span>
            <input
              className={styles.unitInput}
              value={component.unit ?? ''}
              placeholder="kg, °C, m..."
              onChange={(event) =>
                onComponentUpdate?.(component.id, { unit: event.target.value.trim() || null })
              }
            />
          </label>
        ) : component.unit ? (
          <span className={styles.unit}>{component.unit}</span>
        ) : null}
      </div>

      {component.min !== null || component.max !== null ? (
        <p className={styles.hint}>{formatRange(component.min, component.max)}</p>
      ) : null}
    </div>
  )
}
