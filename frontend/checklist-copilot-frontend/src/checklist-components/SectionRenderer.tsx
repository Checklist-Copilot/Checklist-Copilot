import { ComponentRenderer } from './ComponentRenderer'
import styles from './SectionRenderer.module.css'
import type { SectionComponent } from './types'
import { componentTitle } from './utils'

type SectionRendererProps = {
  section: SectionComponent
  index?: number
}

export function SectionRenderer({ section, index }: SectionRendererProps) {
  return (
    <section className={styles.section} data-component-id={section.id}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>
            {index !== undefined ? <span className={styles.index}>{index + 1}</span> : null}
            {componentTitle(section)}
          </h2>
          {section.description ? <p className={styles.description}>{section.description}</p> : null}
        </div>
        {section.collapsed ? <span className={styles.collapsedBadge}>Collapsed</span> : null}
      </div>

      {!section.collapsed ? (
        <div className={styles.children}>
          {section.children.map((component) => (
            <ComponentRenderer key={component.id} component={component} />
          ))}
        </div>
      ) : null}
    </section>
  )
}
