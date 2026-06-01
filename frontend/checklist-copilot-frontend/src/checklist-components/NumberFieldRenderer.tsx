import styles from './NumberFieldRenderer.module.css'
import type { NumberFieldComponent } from './types'
import { componentTitle, formatRange } from './utils'

export function NumberFieldRenderer({ component }: { component: NumberFieldComponent }) {
  return (
    <div className={styles.field} data-component-id={component.id}>
      <label className={styles.labelRow} htmlFor={component.id}>
        {componentTitle(component)}
        {component.required ? <span className={styles.requiredBadge}>Required</span> : null}
      </label>
      {component.description ? <p className={styles.description}>{component.description}</p> : null}
      <div className={styles.inputWrap}>
        <input
          id={component.id}
          className={styles.input}
          type="number"
          defaultValue={component.value ?? ''}
          min={component.min ?? undefined}
          max={component.max ?? undefined}
          required={component.required}
        />
        {component.unit ? <span className={styles.unit}>{component.unit}</span> : null}
      </div>
      {component.min !== null || component.max !== null ? (
        <p className={styles.hint}>{formatRange(component.min, component.max)}</p>
      ) : null}
    </div>
  )
}
