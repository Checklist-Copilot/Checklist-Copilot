import { useState } from 'react'
import { FiPlus } from 'react-icons/fi'
import { EditableLabel } from './EditableLabel'
import styles from './TableRenderer.module.css'
import type { TableCellValue, TableColumn, TableColumnType, TableComponent, TableRow } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type TableRendererProps = {
  component: TableComponent
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>) => void
}

type AllowedTableColumnType = Extract<TableColumnType, 'text' | 'number'>

export function TableRenderer({ component, isEditMode = false, onComponentUpdate }: TableRendererProps) {
  const [editingColumnId, setEditingColumnId] = useState<string | null>(null)

  function updateTable(patch: Partial<Pick<TableComponent, 'columns' | 'rows'>>) {
    onComponentUpdate?.(component.id, patch)
  }

  function handleCellChange(rowId: string, column: TableColumn, rawValue: string) {
    const columnType = getColumnType(column)
    const value: TableCellValue = columnType === 'number' ? parseNumberValue(rawValue) : rawValue

    updateTable({
      rows: component.rows.map((row) =>
        row.id === rowId
          ? {
              ...row,
              cells: {
                ...row.cells,
                [column.id]: value,
              },
            }
          : row,
      ),
    })
  }

  function handleAddColumn() {
    const columnId = crypto.randomUUID()

    updateTable({
      columns: [
        ...component.columns,
        {
          id: columnId,
          label: `Column ${component.columns.length + 1}`,
          type: 'text',
        },
      ],
      rows: component.rows.map((row) => ({
        ...row,
        cells: {
          ...row.cells,
          [columnId]: '',
        },
      })),
    })
  }

  function handleAddRow() {
    const row: TableRow = {
      id: crypto.randomUUID(),
      cells: Object.fromEntries(component.columns.map((column) => [column.id, ''])),
    }

    updateTable({ rows: [...component.rows, row] })
  }

  function handleColumnLabelChange(columnId: string, label: string) {
    updateTable({
      columns: component.columns.map((column) => (column.id === columnId ? { ...column, label } : column)),
    })
  }

  function handleColumnTypeChange(columnId: string, type: AllowedTableColumnType) {
    const targetColumn = component.columns.find((column) => column.id === columnId)
    const currentType = targetColumn ? getColumnType(targetColumn) : 'text'
    const rows =
      currentType === type
        ? component.rows
        : component.rows.map((row) => ({
            ...row,
            cells: {
              ...row.cells,
              [columnId]: getDefaultValueForType(type, row.cells[columnId]),
            },
          }))

    updateTable({
      columns: component.columns.map((column) =>
        column.id === columnId
          ? { ...column, type, valueType: type, unit: type === 'number' ? column.unit ?? null : null }
          : column,
      ),
      rows,
    })
  }

  function handleColumnUnitChange(columnId: string, unit: string) {
    updateTable({
      columns: component.columns.map((column) =>
        column.id === columnId ? { ...column, unit: unit.trim() || null } : column,
      ),
    })
  }

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
              {component.columns.map((column, columnIndex) => (
                <th key={column.id}>
                  {isEditMode ? (
                    <div className={styles.headerCell}>
                      <button
                        type="button"
                        className={styles.columnButton}
                        onClick={(event) => {
                          event.stopPropagation()
                          setEditingColumnId((currentId) => (currentId === column.id ? null : column.id))
                        }}
                      >
                        {column.label || 'Untitled column'}
                      </button>

                      {editingColumnId === column.id ? (
                        <div
                          className={`${styles.columnPopover} ${
                            columnIndex > 0 ? styles.columnPopoverOffset : ''
                          } ${columnIndex === 0 ? styles.firstColumnPopover : ''}`}
                          onClick={(event) => event.stopPropagation()}
                        >
                          <div className={styles.popoverHeader}>
                            <span>Column settings</span>
                            <button
                              type="button"
                              className={styles.doneButton}
                              onClick={() => setEditingColumnId(null)}
                            >
                              Done
                            </button>
                          </div>

                          <label className={styles.popoverField}>
                            <span>Name</span>
                            <input
                              value={column.label}
                              onChange={(event) => handleColumnLabelChange(column.id, event.target.value)}
                            />
                          </label>

                          <div className={styles.popoverField}>
                            <span>Type</span>
                            <div className={styles.typeOptions}>
                              {getAvailableColumnTypes().map((type) => (
                                <button
                                  key={type}
                                  type="button"
                                  className={`${styles.typeOption} ${
                                    getColumnType(column) === type ? styles.typeOptionActive : ''
                                  }`}
                                  onClick={() => {
                                    handleColumnTypeChange(column.id, type)
                                  }}
                                >
                                  {formatColumnType(type)}
                                </button>
                              ))}
                            </div>
                          </div>

                          {getColumnType(column) === 'number' ? (
                            <label className={styles.popoverField}>
                              <span>Unit</span>
                              <input
                                value={column.unit ?? ''}
                                placeholder="kg, degC, m..."
                                onChange={(event) => handleColumnUnitChange(column.id, event.target.value)}
                              />
                            </label>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    column.label
                  )}
                </th>
              ))}
              {isEditMode ? (
                <th className={styles.addColumnHeader}>
                  <button
                    type="button"
                    className={styles.addButton}
                    aria-label="Add table column"
                    onClick={(event) => {
                      event.stopPropagation()
                      handleAddColumn()
                    }}
                  >
                    <FiPlus />
                  </button>
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {component.rows.map((row) => (
              <tr key={row.id}>
                {component.columns.map((column) => (
                  <td key={column.id}>{renderEditableCell(row, column, handleCellChange)}</td>
                ))}
                {isEditMode ? <td className={styles.controlCell} aria-hidden="true" /> : null}
              </tr>
            ))}
            {isEditMode ? (
              <tr>
                <td colSpan={component.columns.length + 1} className={styles.addRowCell}>
                  <button
                    type="button"
                    className={styles.addRowButton}
                    onClick={(event) => {
                      event.stopPropagation()
                      handleAddRow()
                    }}
                  >
                    <FiPlus />
                    Add row
                  </button>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function renderEditableCell(
  row: TableRow,
  column: TableColumn,
  onChange: (rowId: string, column: TableColumn, value: string) => void,
) {
  const columnType = getColumnType(column)
  const value = row.cells[column.id]

  return (
    <div className={columnType === 'number' && column.unit ? styles.numberCell : undefined}>
      <input
        className={styles.cellInput}
        type={columnType === 'number' ? 'number' : 'text'}
        value={stringifyCellValue(value)}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => onChange(row.id, column, event.target.value)}
      />
      {columnType === 'number' && column.unit ? <span className={styles.cellUnit}>{column.unit}</span> : null}
    </div>
  )
}

function getColumnType(column: TableColumn): AllowedTableColumnType {
  const columnType = column.type ?? column.valueType
  return columnType === 'number' ? 'number' : 'text'
}

function parseNumberValue(value: TableCellValue | string): number | null {
  if (value === null || value === undefined || value === '') return null

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function stringifyCellValue(value: TableCellValue) {
  return value === null || value === undefined ? '' : String(value)
}

function getDefaultValueForType(type: AllowedTableColumnType, previousValue: TableCellValue): TableCellValue {
  if (type === 'number') return parseNumberValue(previousValue)

  return stringifyCellValue(previousValue)
}

function formatColumnType(type: AllowedTableColumnType) {
  if (type === 'number') return 'Number'

  return 'Text'
}

function getAvailableColumnTypes(): AllowedTableColumnType[] {
  return ['text', 'number']
}
