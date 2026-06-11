import { EditableLabel } from './EditableLabel'
import styles from './TableRenderer.module.css'
import type { TableCellValue, TableColumn, TableComponent } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type TableRendererProps = {
  component: TableComponent
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
}

export function TableRenderer({ component, isEditMode = false, onComponentUpdate }: TableRendererProps) {
  return (
    <section className={styles.block} data-component-id={component.id}>
      <h3 className={styles.title}>
        <EditableLabel
          value={componentTitle(component)}
          fallbackValue={defaultLabelForType(component.type)}
          isEditMode={isEditMode}
          ariaLabel="Table label"
          onChange={(value) => onComponentUpdate?.(component.id, { label: value })}
        />
      </h3>
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
