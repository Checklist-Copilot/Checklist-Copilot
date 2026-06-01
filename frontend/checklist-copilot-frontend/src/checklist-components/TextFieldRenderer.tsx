import styles from './TextFieldRenderer.module.css'
import type { TextFieldComponent } from './types'
import { componentTitle } from './utils'

export function TextFieldRenderer({ component }: { component: TextFieldComponent }) {
  return (
    <div className={styles.field} data-component-id={component.id}>
      <label className={styles.labelRow} htmlFor={component.id}>
        {componentTitle(component)}
        {component.required ? <span className={styles.requiredBadge}>Required</span> : null}
      </label>

      {component.description ? <p className={styles.description}>{component.description}</p> : null}

      {component.multiline ? (
        <textarea
          id={component.id}
          className={styles.textarea}
          defaultValue={component.value}
          placeholder={component.placeholder ?? undefined}
          required={component.required}
        />
      ) : (
        <input
          id={component.id}
          className={styles.input}
          type="text"
          defaultValue={component.value}
          placeholder={component.placeholder ?? undefined}
          required={component.required}
        />
      )}
    </div>
  )
}
