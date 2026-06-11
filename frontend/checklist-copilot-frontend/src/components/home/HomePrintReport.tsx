import { ChecklistPrintReport, type ChecklistRoot } from '../../checklist-components'
import type { Checklist, ChecklistSummary } from '../../types/checklist'
import { getChecklistStatus, getSelectedItemCounts } from './homePageUtils'

type HomePrintReportProps = {
  pdfChecklist: Checklist | null
  selectedChecklist: ChecklistSummary | null
}

export function HomePrintReport({ pdfChecklist, selectedChecklist }: HomePrintReportProps) {
  const pdfChecklistRoot = isChecklistRoot(pdfChecklist?.checklist) ? pdfChecklist.checklist : null

  if (!pdfChecklist || !selectedChecklist || !pdfChecklistRoot) return null

  const statusCounts = getSelectedItemCounts(selectedChecklist)
  const completionPercent = selectedChecklist.total_items > 0
    ? Math.round((selectedChecklist.completed_items / selectedChecklist.total_items) * 100)
    : 0

  return (
    <ChecklistPrintReport
      title={pdfChecklist.title}
      description={pdfChecklist.description}
      checklist={pdfChecklistRoot}
      stats={[
        { label: 'Status', value: getChecklistStatus(selectedChecklist) },
        { label: 'Total items', value: selectedChecklist.total_items },
        { label: 'Completion', value: `${completionPercent}%` },
        { label: 'In progress', value: statusCounts['In Progress'] },
        { label: 'Not started', value: statusCounts['Not Started'] },
        { label: 'Completed', value: selectedChecklist.completed_items },
      ]}
    />
  )
}

function isChecklistRoot(value: unknown): value is ChecklistRoot {
  if (!value || typeof value !== 'object') return false

  const candidate = value as { type?: unknown; children?: unknown }
  return candidate.type === 'root' && Array.isArray(candidate.children)
}
