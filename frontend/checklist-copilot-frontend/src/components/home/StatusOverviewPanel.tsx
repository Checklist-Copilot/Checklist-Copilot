import CustomDropdown, { type DropdownOption } from '../CustomDropdown'
import type { ChecklistSummary } from '../../types/checklist'
import styles from '../../page-styles/HomePage.module.css'
import { CiFlag1 } from 'react-icons/ci'
import { GoClock } from 'react-icons/go'
import { IoCheckmarkCircleOutline } from 'react-icons/io5'
import { getDonutStyle, getSelectedItemCounts, getStatusCounts } from './homePageUtils'

type StatusOverviewPanelProps = {
  checklists: ChecklistSummary[]
  selectedChecklist: ChecklistSummary | null
  selectedChecklistId: string
  onSelectChecklist: (id: string) => void
  onExportPdf: () => void
  isPreparingPdf: boolean
}

export function StatusOverviewPanel({
  checklists,
  selectedChecklist,
  selectedChecklistId,
  onSelectChecklist,
  onExportPdf,
  isPreparingPdf,
}: StatusOverviewPanelProps) {
  const totalChecklists = checklists.length
  const isSingleChecklistView = selectedChecklist !== null
  const totalItems = checklists.reduce((sum, checklist) => sum + checklist.total_items, 0)
  const completedItems = checklists.reduce((sum, checklist) => sum + checklist.completed_items, 0)
  const displayedTotal = selectedChecklist?.total_items ?? totalItems
  const displayedCompleted = selectedChecklist?.completed_items ?? completedItems
  const statusCounts = selectedChecklist ? getSelectedItemCounts(selectedChecklist) : getStatusCounts(checklists)
  const completionPercent = selectedChecklist
    ? displayedTotal > 0
      ? Math.round((displayedCompleted / displayedTotal) * 100)
      : 0
    : totalChecklists > 0
      ? Math.round((statusCounts.Completed / totalChecklists) * 100)
      : 0
  const checklistOptions: DropdownOption<string>[] = [
    { value: '', label: 'All checklists', tone: 'purple' },
    ...checklists.map((checklist) => ({ value: checklist.id, label: checklist.title, tone: 'neutral' as const })),
  ]

  return (
    <div className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <h2 className={styles.panelTitle}>Status Overview</h2>
          <p className={styles.panelSubtitle}>
            {isSingleChecklistView ? 'Item status for the selected checklist' : 'Checklist status across your dashboard'}
          </p>
        </div>

        <div className={styles.selectLabel}>
          <span>Checklist</span>
          <CustomDropdown
            label="Checklist"
            value={selectedChecklistId}
            options={checklistOptions}
            onChange={onSelectChecklist}
            disabled={checklists.length === 0}
          />
        </div>
      </div>

      <div className={styles.statusContent}>
        <div className={styles.donut} style={getDonutStyle(statusCounts)}>
          <span className={styles.donutNumber}>{completionPercent}%</span>
          <span className={styles.donutLabel}>complete</span>
        </div>

        <div className={styles.statusList}>
          <div>
            <span className={styles.redDot}>
              <CiFlag1 />
            </span>
            <span>Not Started</span>
            <strong>{statusCounts['Not Started']}</strong>
          </div>
          <div>
            <span className={styles.yellowDot}>
              <GoClock />
            </span>
            <span>In Progress</span>
            <strong>{statusCounts['In Progress']}</strong>
          </div>
          <div>
            <span className={styles.greenDot}>
              <IoCheckmarkCircleOutline />
            </span>
            <span>Completed</span>
            <strong>{statusCounts.Completed}</strong>
          </div>
        </div>
      </div>

      <div className={styles.metricGrid}>
        <div>
          <span>{isSingleChecklistView ? 'Items' : 'Checklists'}</span>
          <strong>{selectedChecklist ? selectedChecklist.total_items : totalChecklists}</strong>
        </div>
        {isSingleChecklistView ? (
          <div>
            <span>Completed items</span>
            <strong>{displayedCompleted}</strong>
          </div>
        ) : null}
        <div>
          <span>Last updated</span>
          <strong>
            {selectedChecklist
              ? new Date(selectedChecklist.updated_at).toLocaleDateString()
              : checklists[0]
                ? new Date(checklists[0].updated_at).toLocaleDateString()
                : 'None'}
          </strong>
        </div>
      </div>

      <button
        className={styles.pdfButton}
        type="button"
        onClick={onExportPdf}
        disabled={!selectedChecklist || isPreparingPdf}
      >
        {isPreparingPdf ? 'Preparing PDF...' : 'Create PDF'}
      </button>
    </div>
  )
}
