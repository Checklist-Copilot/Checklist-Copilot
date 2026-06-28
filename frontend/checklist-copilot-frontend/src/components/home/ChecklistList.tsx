import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FaPlus, FaSearch } from 'react-icons/fa'
import CustomDropdown, { type DropdownOption } from '../CustomDropdown'
import type { ChecklistSummary } from '../../types/checklist'
import styles from '../../page-styles/HomePage.module.css'
import type { ChecklistStatus, SortMode } from './types'
import { getChecklistStatus, getOwnerName } from './homePageUtils'
import { ChecklistCard } from './ChecklistCard'

type ChecklistListProps = {
  checklists: ChecklistSummary[]
  selectedChecklistId: string
  ownerNames: Record<string, string>
  isLoading: boolean
  errorMessage: string | null
  onSelectChecklist: (id: string) => void
  onDelete: (id: string) => void
}

const statusFilterOptions = [
  { value: 'all', label: 'All statuses', tone: 'purple' },
  { value: 'Not Started', label: 'Not Started', tone: 'red' },
  { value: 'In Progress', label: 'In Progress', tone: 'yellow' },
  { value: 'Completed', label: 'Completed', tone: 'green' },
] satisfies DropdownOption<ChecklistStatus | 'all'>[]

const sortOptions = [
  { value: 'updatedDesc', label: 'Updated newest', tone: 'purple' },
  { value: 'updatedAsc', label: 'Updated oldest', tone: 'purple' },
  { value: 'createdDesc', label: 'Created newest', tone: 'purple' },
  { value: 'createdAsc', label: 'Created oldest', tone: 'purple' },
] satisfies DropdownOption<SortMode>[]

export function ChecklistList({
  checklists,
  selectedChecklistId,
  ownerNames,
  isLoading,
  errorMessage,
  onSelectChecklist,
  onDelete,
}: ChecklistListProps) {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<ChecklistStatus | 'all'>('all')
  const [sortMode, setSortMode] = useState<SortMode>('updatedDesc')
  const [searchTerm, setSearchTerm] = useState('')

  const normalizedSearchTerm = searchTerm.trim().toLowerCase()
  const sortedChecklists = checklists
    .filter((checklist) => {
      const matchesStatus = statusFilter === 'all' || getChecklistStatus(checklist) === statusFilter
      const matchesSearch = checklist.title.toLowerCase().includes(normalizedSearchTerm)

      return matchesStatus && matchesSearch
    })
    .sort((a, b) => {
      const updatedDiff = new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      const createdDiff = new Date(b.created_at).getTime() - new Date(a.created_at).getTime()

      if (sortMode === 'updatedAsc') return -updatedDiff
      if (sortMode === 'createdDesc') return createdDiff
      if (sortMode === 'createdAsc') return -createdDiff
      return updatedDiff
    })

  return (
    <section className={styles.content}>
      <div className={styles.listHeader}>
        <h2 className={styles.sectionTitle}>My Checklists</h2>

        <div className={styles.listTools}>
          <label className={styles.searchLabel}>
            <FaSearch />
            <span className={styles.visuallyHidden}>Search checklist by name</span>
            <input
              type="search"
              placeholder="Search by name"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>

          <div className={styles.listFilters}>
            <CustomDropdown
              label="Filter by status"
              value={statusFilter}
              options={statusFilterOptions}
              onChange={setStatusFilter}
            />

            <CustomDropdown label="Sort checklists" value={sortMode} options={sortOptions} onChange={setSortMode} />
          </div>

          <button type="button" className={`${styles.newButton} ${styles.mobileNewButton}`} onClick={() => navigate('/checklist/new')}>
            <FaPlus />
            New Checklist
          </button>
        </div>
      </div>

      {isLoading ? <p className={styles.message}>Loading checklists...</p> : null}
      {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}

      {!isLoading && !errorMessage && checklists.length === 0 ? (
        <div className={styles.emptyState}>
          <h3>No checklists yet</h3>
          <p>Create your first checklist to start managing inspections.</p>
          <button type="button" className={styles.openButton} onClick={() => navigate('/checklist/new')}>
            <FaPlus />
            New Checklist
          </button>
        </div>
      ) : null}

      {!isLoading && !errorMessage && checklists.length > 0 && sortedChecklists.length === 0 ? (
        <div className={styles.emptyState}>
          <h3>No matching checklists</h3>
          <p>Try another name, status, or sort option.</p>
        </div>
      ) : null}

      {!isLoading && !errorMessage && sortedChecklists.length > 0 ? (
        <div className={styles.cardGrid}>
          {sortedChecklists.map((checklist) => (
            <ChecklistCard
              key={checklist.id}
              checklist={checklist}
              isSelected={selectedChecklistId === checklist.id}
              ownerName={getOwnerName(ownerNames, checklist.user_id)}
              onViewStats={onSelectChecklist}
              onDelete={onDelete}
            />
          ))}
        </div>
      ) : null}
    </section>
  )
}
