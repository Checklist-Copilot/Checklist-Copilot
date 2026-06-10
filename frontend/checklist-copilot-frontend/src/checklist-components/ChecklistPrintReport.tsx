import type { CSSProperties } from 'react'
import styles from './ChecklistPrintReport.module.css'
import type { ChecklistComponent, ChecklistRoot } from './types'
import { componentTitle } from './utils'

type ChecklistPrintStat = {
  label: string
  value: string | number
}

type ChecklistPrintReportProps = {
  title: string
  description?: string | null
  checklist: ChecklistRoot
  stats: ChecklistPrintStat[]
}

/*
16:27
ChecklistPrintReport.tsx is a reusable print/PDF component that receives a checklist, title, description, and stats, then 
renders a clean report with the logo, summary stats, and checklist content underneath. It walks through the checklist JSON and 
converts sections, checkboxes, fields, images, and tables into simple printable text with indentation and required-field labels.*/

export function ChecklistPrintReport({
  title,
  description,
  checklist,
  stats,
}: ChecklistPrintReportProps) {
  return (
    <section className={styles.report} data-print-report aria-hidden="true">
      <header className={styles.header}>
        <img src="/src/assets/logo_cropped.png" alt="Checkly logo" className={styles.logo} />
        <p className={styles.eyebrow}>Checklist Report</p>
        <h1>{title}</h1>
        <p>{description ?? 'No description.'}</p>
      </header>

      <div className={styles.stats}>
        {stats.map((stat) => (
          <div key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
          </div>
        ))}
      </div>

      <div className={styles.checklistText}>
        {checklist.children.map((component, index) => (
          <PrintChecklistComponent
            key={component.id}
            component={component}
            level={0}
            indexPath={`${index + 1}`}
          />
        ))}
      </div>
    </section>
  )
}

function PrintChecklistComponent({
  component,
  level,
  indexPath,
}: {
  component: ChecklistComponent
  level: number
  indexPath: string
}) {
  const title = componentTitle(component)

  if (component.type === 'section') {
    return (
      <section className={styles.section} style={{ '--print-level': level } as CSSProperties}>
        <h2 className={styles.sectionTitle}>
          {indexPath}. {title}
        </h2>
        {component.description ? <p className={styles.description}>{component.description}</p> : null}
        {component.children.map((child, index) => (
          <PrintChecklistComponent
            key={child.id}
            component={child}
            level={level + 1}
            indexPath={`${indexPath}.${index + 1}`}
          />
        ))}
      </section>
    )
  }

  if (component.type === 'checkboxGroup' || component.type === 'checkboxContainer') {
    return (
      <section className={styles.group} style={{ '--print-level': level } as CSSProperties}>
        <h3 className={styles.groupTitle}>
          {indexPath}. {title}
        </h3>
        {component.description ? <p className={styles.description}>{component.description}</p> : null}
        <ul className={styles.list}>
          {component.items.map((item) => (
            <li key={item.id}>
              {item.checked ? '[x]' : '[ ]'} {componentTitle(item)}
              {item.required ? <span className={styles.required}>Required</span> : null}
            </li>
          ))}
        </ul>
      </section>
    )
  }

  if (component.type === 'checkbox' || component.type === 'checkboxItem') {
    return (
      <p className={styles.item} style={{ '--print-level': level } as CSSProperties}>
        {component.checked ? '[x]' : '[ ]'} {indexPath}. {title}
        {component.required ? <span className={styles.required}>Required</span> : null}
      </p>
    )
  }

  if (component.type === 'textField') {
    return (
      <p className={styles.item} style={{ '--print-level': level } as CSSProperties}>
        {indexPath}. {title}: {component.value || 'Not filled'}
        {component.required ? <span className={styles.required}>Required</span> : null}
      </p>
    )
  }

  if (component.type === 'numberField' || component.type === 'numericField') {
    const value = component.value === null || component.value === undefined ? 'Not filled' : component.value

    return (
      <p className={styles.item} style={{ '--print-level': level } as CSSProperties}>
        {indexPath}. {title}: {value}
        {component.unit ? ` ${component.unit}` : ''}
        {component.required ? <span className={styles.required}>Required</span> : null}
      </p>
    )
  }

  if (component.type === 'imageBlock' || component.type === 'imagesSection') {
    return (
      <p className={styles.item} style={{ '--print-level': level } as CSSProperties}>
        {indexPath}. {title}: {component.images.length} image{component.images.length === 1 ? '' : 's'} attached
      </p>
    )
  }

  if (component.type === 'table') {
    return (
      <section className={styles.group} style={{ '--print-level': level } as CSSProperties}>
        <h3 className={styles.groupTitle}>
          {indexPath}. {title}
        </h3>
        {component.description ? <p className={styles.description}>{component.description}</p> : null}
        <table className={styles.table}>
          <thead>
            <tr>
              {component.columns.map((column) => (
                <th key={column.id}>{column.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {component.rows.map((row) => (
              <tr key={row.id}>
                {component.columns.map((column) => (
                  <td key={column.id}>{formatPrintValue(row.cells[column.id])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    )
  }

  return null
}

function formatPrintValue(value: unknown) {
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}
