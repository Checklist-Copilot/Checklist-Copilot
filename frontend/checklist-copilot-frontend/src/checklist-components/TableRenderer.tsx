import { useLayoutEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { createPortal } from 'react-dom'
import { FiChevronDown, FiPlus, FiX } from 'react-icons/fi'
import type { ChecklistOperation } from '../api/checklist'
import { ConfirmationModal } from '../components/ConfirmationModal'
import { EditableLabel } from './EditableLabel'
import styles from './TableRenderer.module.css'
import type { TableCellValue, TableColumn, TableColumnType, TableComponent, TableRow } from './types'
import { componentTitle, defaultLabelForType } from './utils'

type TableRendererProps = {
  component: TableComponent
  isEditMode?: boolean
  onComponentUpdate?: (componentId: string, patch: Record<string, unknown>, operation?: ChecklistOperation) => void
}

type PendingDeletion =
  | { type: 'column'; column: TableColumn }
  | { type: 'row'; row: TableRow }

type ColumnPopoverPosition = {
  top: number
  left: number
  arrowLeft: number
}

type AllowedTableColumnType = Extract<TableColumnType, 'text' | 'number'>

// Renders editable checklist tables and owns table-specific row/column controls.
// Structural deletions are confirmed here, applied optimistically, then handed to the parent for immediate persistence.
export function TableRenderer({ component, isEditMode = false, onComponentUpdate }: TableRendererProps) {
  const [editingColumnId, setEditingColumnId] = useState<string | null>(null)
  const [closingColumnId, setClosingColumnId] = useState<string | null>(null)
  const [pendingDeletion, setPendingDeletion] = useState<PendingDeletion | null>(null)
  const [popoverPosition, setPopoverPosition] = useState<ColumnPopoverPosition | null>(null)
  const columnButtonRefs = useRef(new Map<string, HTMLButtonElement>())

  useLayoutEffect(() => {
    if (!editingColumnId) return
    const activeColumnId = editingColumnId

    function updatePopoverPosition() {
      const button = columnButtonRefs.current.get(activeColumnId)
      if (!button) return

      const rect = button.getBoundingClientRect()
      const columnIndex = component.columns.findIndex((column) => column.id === activeColumnId)
      const popoverWidth = columnIndex === 0 ? 260 : 240
      const preferredLeft = columnIndex === 0 ? rect.left : rect.left + rect.width / 2 - popoverWidth / 2
      const left = Math.min(Math.max(preferredLeft, 12), window.innerWidth - popoverWidth - 12)
      const arrowLeft = Math.min(Math.max(rect.left + rect.width / 2 - left - 5, 16), popoverWidth - 24)

      setPopoverPosition({ top: rect.bottom + 8, left, arrowLeft })
    }

    updatePopoverPosition()
    window.addEventListener('resize', updatePopoverPosition)
    window.addEventListener('scroll', updatePopoverPosition, true)

    return () => {
      window.removeEventListener('resize', updatePopoverPosition)
      window.removeEventListener('scroll', updatePopoverPosition, true)
    }
  }, [component.columns, editingColumnId])

  function updateTable(patch: Partial<Pick<TableComponent, 'columns' | 'rows'>>) {
    onComponentUpdate?.(component.id, patch)
  }

  function handleCellChange(rowId: string, column: TableColumn, rawValue: string) {
    const columnType = getColumnType(column)
    if (columnType === 'number' && !isNumericCellInput(rawValue)) return

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
      cells: Object.fromEntries(component.columns.map((column) => [column.id, getEmptyCellValue(column)])),
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

  function openColumnSettings(columnId: string) {
    setClosingColumnId(null)
    setEditingColumnId(columnId)
  }

  function closeColumnSettings() {
    if (!editingColumnId || closingColumnId) return
    setClosingColumnId(editingColumnId)
  }

  function handleColumnSettingsAnimationEnd(columnId: string) {
    if (closingColumnId !== columnId) return
    setEditingColumnId(null)
    setClosingColumnId(null)
  }

  function handleConfirmDeletion() {
    if (!pendingDeletion) return

    if (pendingDeletion.type === 'column') {
      const columnId = pendingDeletion.column.id
      const patch = {
        columns: component.columns.filter((column) => column.id !== columnId),
        rows: component.rows.map((row) => ({
          ...row,
          cells: omitCell(row.cells, columnId),
        })),
      }

      onComponentUpdate?.(component.id, patch, { operation: 'deleteTableColumn', targetId: component.id, columnId })
      setEditingColumnId(null)
      setClosingColumnId(null)
    } else {
      const rowId = pendingDeletion.row.id
      const patch = { rows: component.rows.filter((row) => row.id !== rowId) }

      onComponentUpdate?.(component.id, patch, { operation: 'deleteTableRow', targetId: component.id, rowId })
    }

    setPendingDeletion(null)
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
                      <div className={styles.headerActions}>
                        <button
                          type="button"
                          ref={(button) => {
                            if (button) columnButtonRefs.current.set(column.id, button)
                            else columnButtonRefs.current.delete(column.id)
                          }}
                          className={`${styles.columnButton} ${editingColumnId === column.id ? styles.columnButtonOpen : ''}`}
                          aria-expanded={editingColumnId === column.id && closingColumnId !== column.id}
                          onClick={(event) => {
                            event.stopPropagation()
                            if (editingColumnId === column.id) {
                              closeColumnSettings()
                            } else {
                              openColumnSettings(column.id)
                            }
                          }}
                        >
                          <span className={styles.columnLabel}>{column.label || 'Untitled column'}</span>
                          <FiChevronDown className={styles.columnChevron} aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          className={styles.deleteControlButton}
                          aria-label={`Delete ${column.label || 'table column'}`}
                          onClick={(event) => {
                            event.stopPropagation()
                            setPendingDeletion({ type: 'column', column })
                          }}
                        >
                          <FiX />
                        </button>
                      </div>

                      {editingColumnId === column.id && popoverPosition ? createPortal(
                        <div
                          className={`${styles.columnPopover} ${columnIndex === 0 ? styles.firstColumnPopover : ''} ${
                            closingColumnId === column.id ? styles.columnPopoverClosing : ''
                          }`}
                          style={{
                            top: popoverPosition.top,
                            left: popoverPosition.left,
                            '--popover-arrow-left': `${popoverPosition.arrowLeft}px`,
                          } as CSSProperties}
                          onClick={(event) => event.stopPropagation()}
                          onAnimationEnd={() => handleColumnSettingsAnimationEnd(column.id)}
                        >
                          <div className={styles.popoverHeader}>
                            <span>Column settings</span>
                            <button
                              type="button"
                              className={styles.doneButton}
                              onClick={closeColumnSettings}
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
                        </div>,
                        document.body,
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
                    className={styles.addColumnButton}
                    aria-label="Add table column"
                    onClick={(event) => {
                      event.stopPropagation()
                      handleAddColumn()
                    }}
                  >
                    <FiPlus />
                    Add column
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
                {isEditMode ? (
                  <td className={styles.controlCell}>
                    <button
                      type="button"
                      className={styles.deleteControlButton}
                      aria-label="Delete table row"
                      onClick={(event) => {
                        event.stopPropagation()
                        setPendingDeletion({ type: 'row', row })
                      }}
                    >
                      <FiX />
                    </button>
                  </td>
                ) : null}
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

      <ConfirmationModal
        isOpen={pendingDeletion !== null}
        title={pendingDeletion?.type === 'column' ? 'Delete table column?' : 'Delete table row?'}
        message={getDeletionMessage(pendingDeletion)}
        confirmLabel="Delete"
        onConfirm={handleConfirmDeletion}
        onClose={() => setPendingDeletion(null)}
      />
    </section>
  )
}

function getDeletionMessage(pendingDeletion: PendingDeletion | null) {
  if (!pendingDeletion) return ''

  if (pendingDeletion.type === 'column') {
    return `This will remove the "${pendingDeletion.column.label || 'Untitled column'}" column and all of its cell values.`
  }

  return 'This will remove the row and all of its cell values.'
}

function omitCell(cells: Record<string, TableCellValue>, columnId: string) {
  const remainingCells = { ...cells }
  delete remainingCells[columnId]
  return remainingCells
}

function getEmptyCellValue(column: TableColumn): TableCellValue {
  return getColumnType(column) === 'number' ? null : ''
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
        type="text"
        inputMode={columnType === 'number' ? 'decimal' : undefined}
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

function isNumericCellInput(value: string) {
  return value === '' || /^\d*(\.\d*)?$/.test(value)
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
