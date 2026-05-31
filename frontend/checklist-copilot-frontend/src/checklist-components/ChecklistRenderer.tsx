import { ComponentRenderer } from './ComponentRenderer'
import styles from './ChecklistRenderer.module.css'
import type { ChecklistRoot } from './types'

export function ChecklistRenderer({ checklist }: { checklist: ChecklistRoot }) {
  return (
    <div className={styles.root} data-checklist-id={checklist.id}>
      {checklist.children.map((component, index) => (
        <ComponentRenderer key={component.id} component={component} index={index} />
      ))}
    </div>
  )
}
