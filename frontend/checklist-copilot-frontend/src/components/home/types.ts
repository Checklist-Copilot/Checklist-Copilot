export type ChecklistStatus = 'Not Started' | 'In Progress' | 'Completed'
export type ActivityMode = 'created' | 'inProgress' | 'completed'
export type SortMode = 'updatedDesc' | 'updatedAsc' | 'createdDesc' | 'createdAsc'

export type ActivityDay = {
  key: string
  label: string
  count: number
}
