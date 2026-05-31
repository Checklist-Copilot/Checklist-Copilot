import styles from './TableRenderer.module.css'
import type { TableCellValue, TableColumn, TableComponent } from './types'
import { componentTitle } from './utils'

export function TableRenderer({ component }: { component: TableComponent }) {
  return (
    <section className={styles.block} data-component-id={component.id}>
      <h3 className={styles.title}>{componentTitle(component)}</h3>
      {component.description ? <p className={styles.description}>{component.description}</p> : null}
      <div className={styles.wrap}>
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
                  <td key={column.id}>{renderTableCell(row.cells[column.id], column)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function renderTableCell(value: TableCellValue, column: TableColumn) {
  const columnType = column.type ?? column.valueType

  if (columnType === 'checkbox') {
    return <input className={styles.checkbox} type="checkbox" checked={Boolean(value)} readOnly />
  }

  return value === null || value === undefined ? '' : String(value)
}
