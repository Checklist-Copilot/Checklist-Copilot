import { CheckboxRenderer } from './CheckboxRenderer'
import styles from './CheckboxGroupRenderer.module.css'
import type { CheckboxGroupComponent } from './types'
import { componentTitle } from './utils'

export function CheckboxGroupRenderer({ component }: { component: CheckboxGroupComponent }) {
  return (
    <section className={styles.group} data-component-id={component.id} aria-labelledby={`${component.id}-title`}>
      <div className={styles.header}>
        <h3 className={styles.title} id={`${component.id}-title`}>
          {componentTitle(component)}
        </h3>
        {component.description ? <p className={styles.description}>{component.description}</p> : null}
      </div>

      <div className={styles.list}>
        {component.items.map((item) => (
          <CheckboxRenderer key={item.id} component={item} />
        ))}
      </div>
    </section>
  )
}
