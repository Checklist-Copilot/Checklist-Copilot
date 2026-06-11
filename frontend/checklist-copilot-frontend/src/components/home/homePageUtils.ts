import type { CSSProperties } from 'react'
import type { ChecklistSummary } from '../../types/checklist'
import type { ActivityDay, ActivityMode, ChecklistStatus } from './types'

export function getChecklistStatus(checklist: ChecklistSummary): ChecklistStatus {
  if (checklist.total_items > 0 && checklist.completed_items >= checklist.total_items) {
    return 'Completed'
  }

  if (checklist.edited_items === 0 && checklist.completed_items === 0) {
    return 'Not Started'
  }

  return 'In Progress'
}

export function getStatusCounts(checklists: ChecklistSummary[]) {
  return checklists.reduce(
    (counts, checklist) => {
      counts[getChecklistStatus(checklist)] += 1
      return counts
    },
    { 'Not Started': 0, 'In Progress': 0, Completed: 0 } satisfies Record<ChecklistStatus, number>,
  )
}

export function getSelectedItemCounts(checklist: ChecklistSummary) {
  const completed = checklist.completed_items
  const touched = Math.max(checklist.edited_items, checklist.completed_items)
  const inProgress = Math.max(touched - checklist.completed_items, 0)
  const notStarted = Math.max(checklist.total_items - touched, 0)

  return {
    'Not Started': notStarted,
    'In Progress': inProgress,
    Completed: completed,
  } satisfies Record<ChecklistStatus, number>
}

export function getActivityDays(checklists: ChecklistSummary[], mode: ActivityMode): ActivityDay[] {
  const today = new Date()
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today)
    date.setHours(0, 0, 0, 0)
    date.setDate(today.getDate() - (6 - index))

    return {
      key: date.toDateString(),
      label: date.toLocaleDateString(undefined, { weekday: 'short' }),
      count: 0,
    }
  })

  const countsByDay = new Map(days.map((day) => [day.key, day.count]))

  checklists.forEach((checklist) => {
    const status = getChecklistStatus(checklist)
    const shouldCount =
      mode === 'created' ||
      (mode === 'inProgress' && status === 'In Progress') ||
      (mode === 'completed' && status === 'Completed')

    if (!shouldCount) return

    const activityDate = new Date(mode === 'created' ? checklist.created_at : checklist.updated_at)
    activityDate.setHours(0, 0, 0, 0)
    const key = activityDate.toDateString()

    if (countsByDay.has(key)) {
      countsByDay.set(key, (countsByDay.get(key) ?? 0) + 1)
    }
  })

  return days.map((day) => ({
    ...day,
    count: countsByDay.get(day.key) ?? 0,
  }))
}

export function getOwnerName(ownerNames: Record<string, string>, ownerId: string) {
  return ownerNames[ownerId] ?? ownerId
}

export function getDonutStyle(statusCounts: Record<ChecklistStatus, number>) {
  const statusTotal = statusCounts['Not Started'] + statusCounts['In Progress'] + statusCounts.Completed
  const notStartedEnd = statusTotal > 0 ? (statusCounts['Not Started'] / statusTotal) * 100 : 0
  const inProgressEnd = statusTotal > 0 ? notStartedEnd + (statusCounts['In Progress'] / statusTotal) * 100 : 0

  return {
    '--donut-background':
      statusTotal > 0
        ? `conic-gradient(
            #fb7185 0 ${notStartedEnd}%,
            #d6b95a ${notStartedEnd}% ${inProgressEnd}%,
            #3b9b70 ${inProgressEnd}% 100%
          )`
        : 'conic-gradient(rgba(255, 255, 255, 0.14) 0 100%)',
  } as CSSProperties & Record<'--donut-background', string>
}
