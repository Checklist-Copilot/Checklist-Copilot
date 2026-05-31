import styles from './CheckboxRenderer.module.css'
import type { CheckboxComponent } from './types'
import { componentTitle } from './utils'

export function CheckboxRenderer({ component }: { component: CheckboxComponent }) {
  return (
    <label className={styles.item} data-component-id={component.id}>
      <input type="checkbox" defaultChecked={component.checked} required={component.required} />
      <span>{componentTitle(component)}</span>
      {component.required ? <span className={styles.requiredBadge}>Required</span> : null}
    </label>
  )
}
