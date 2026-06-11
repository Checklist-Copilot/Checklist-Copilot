import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import styles from '../page-styles/HomePage.module.css'
import { getChecklistById, listChecklists } from '../api/checklist'
import { getUserById } from '../api/user'
import type { Checklist, ChecklistSummary } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import { ChecklistPrintReport, type ChecklistRoot } from '../checklist-components'

import {
  FaPlus,
  FaPlay,
  FaUser,
  FaCalendarAlt,
  FaSearch
} from 'react-icons/fa'
import { FaRegEdit } from 'react-icons/fa'

import { IoCheckmarkCircleOutline } from "react-icons/io5";
import { GoClock } from "react-icons/go";
import { CiFlag1 } from "react-icons/ci";
import { ImBin } from "react-icons/im";

import TopBar from '../components/TopBar'
import CustomDropdown, { type DropdownOption } from '../components/CustomDropdown'

type ChecklistStatus = 'Not Started' | 'In Progress' | 'Completed'
type ActivityMode = 'created' | 'inProgress' | 'completed'
type SortMode = 'updatedDesc' | 'updatedAsc' | 'createdDesc' | 'createdAsc'

function getChecklistStatus(checklist: ChecklistSummary): ChecklistStatus {
  if (checklist.total_items > 0 && checklist.completed_items >= checklist.total_items) {
    return 'Completed'
  }

  if (checklist.edited_items === 0 && checklist.completed_items === 0) {
    return 'Not Started'
  }

  return 'In Progress'
}

/*how many checklists have each label*/
function getStatusCounts(checklists: ChecklistSummary[]) {
  return checklists.reduce(
    (counts, checklist) => {
      counts[getChecklistStatus(checklist)] += 1
      return counts
    },
    { 'Not Started': 0, 'In Progress': 0, Completed: 0 } satisfies Record<ChecklistStatus, number>,
  )
}

/*splits all items into not started, in progress, and completed based on backend progress counts.*/
function getSelectedItemCounts(checklist: ChecklistSummary) {
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

/*ounts how many checklists were updated on each of the last seven days*/
function getActivityDays(checklists: ChecklistSummary[], mode: ActivityMode) {
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

function HomePage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const [checklists, setChecklists] = useState<ChecklistSummary[]>([])
  const [selectedChecklistId, setSelectedChecklistId] = useState('')
  const [activityMode, setActivityMode] = useState<ActivityMode>('created')
  const [statusFilter, setStatusFilter] = useState<ChecklistStatus | 'all'>('all')
  const [ownerFilter, setOwnerFilter] = useState('all')
  const [sortMode, setSortMode] = useState<SortMode>('updatedDesc')
  const [searchTerm, setSearchTerm] = useState('')
  const [ownerNames, setOwnerNames] = useState<Record<string, string>>({})
  const [pdfChecklist, setPdfChecklist] = useState<Checklist | null>(null)
  const [isPreparingPdf, setIsPreparingPdf] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  function handleLogout() {
    removeToken()
    navigate('/')
  }

  async function handleExportPdf() {
    if (!selectedChecklistId) return

    setIsPreparingPdf(true)
    setErrorMessage(null)

    try {
      const response = await getChecklistById(selectedChecklistId)
      setPdfChecklist(response)
      window.setTimeout(() => {
        window.print()
        setIsPreparingPdf(false)
      }, 100)
    } catch {
      setErrorMessage('Could not prepare PDF.')
      setIsPreparingPdf(false)
    }
  }

  useEffect(() => {
    if (!isAuthorized) return

    let isMounted = true

    async function fetchChecklists() {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const response = await listChecklists()
        const ownerIds = Array.from(new Set(response.checklists.map((checklist) => checklist.user_id)))
        const owners = await Promise.all(
          ownerIds.map(async (ownerId) => {
            const user = await getUserById(ownerId)
            return [ownerId, user.username] as const
          }),
        )

        if (isMounted) {
          setChecklists(response.checklists)
          setOwnerNames(Object.fromEntries(owners))
        }
      } catch {
        if (isMounted) setErrorMessage('Could not load checklists.')
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    void fetchChecklists()

    return () => {
      isMounted = false
    }
  }, [isAuthorized])

  if (isCheckingAuth) {
    return (
      <main className={styles.page}>
        <p className={styles.message}>Checking session...</p>
      </main>
    )
  }

  if (!isAuthorized) return null

  const totalChecklists = checklists.length
  const selectedChecklist = checklists.find((checklist) => checklist.id === selectedChecklistId) ?? null
  const pdfChecklistRoot = isChecklistRoot(pdfChecklist?.checklist) ? pdfChecklist.checklist : null
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
  const statusTotal = statusCounts['Not Started'] + statusCounts['In Progress'] + statusCounts.Completed
  const notStartedEnd = statusTotal > 0 ? (statusCounts['Not Started'] / statusTotal) * 100 : 0
  const inProgressEnd = statusTotal > 0 ? notStartedEnd + (statusCounts['In Progress'] / statusTotal) * 100 : 0
  const donutStyle = {
    '--donut-background':
      statusTotal > 0
        ? `conic-gradient(
            #fb7185 0 ${notStartedEnd}%,
            #d6b95a ${notStartedEnd}% ${inProgressEnd}%,
            #3b9b70 ${inProgressEnd}% 100%
          )`
        : 'conic-gradient(rgba(255, 255, 255, 0.14) 0 100%)',
  } as CSSProperties & Record<'--donut-background', string>
  const activityDays = getActivityDays(selectedChecklist ? [selectedChecklist] : checklists, activityMode)
  const maxActivityCount = Math.max(...activityDays.map((day) => day.count), 1)
  const activityLabelByMode = {
    created: 'created',
    inProgress: 'set in progress',
    completed: 'completed',
  } satisfies Record<ActivityMode, string>
  const activityAxisLabels = Array.from(
    new Set([maxActivityCount, Math.floor(maxActivityCount / 2), 0]),
  )
  const normalizedSearchTerm = searchTerm.trim().toLowerCase()
  const owners = Array.from(new Set(checklists.map((checklist) => checklist.user_id))).sort()
  const getOwnerName = (ownerId: string) => ownerNames[ownerId] ?? ownerId
  const checklistOptions: DropdownOption<string>[] = [
    { value: '', label: 'All checklists', tone: 'purple' },
    ...checklists.map((checklist) => ({ value: checklist.id, label: checklist.title, tone: 'neutral' as const })),
  ]
  const statusFilterOptions = [
    { value: 'all', label: 'All statuses', tone: 'purple' },
    { value: 'Not Started', label: 'Not Started', tone: 'red' },
    { value: 'In Progress', label: 'In Progress', tone: 'yellow' },
    { value: 'Completed', label: 'Completed', tone: 'green' },
  ] satisfies DropdownOption<ChecklistStatus | 'all'>[]
  const ownerFilterOptions: DropdownOption<string>[] = [
    { value: 'all', label: 'All owners', tone: 'purple' },
    ...owners.map((ownerId) => ({ value: ownerId, label: getOwnerName(ownerId), tone: 'neutral' as const })),
  ]
  const sortOptions = [
    { value: 'updatedDesc', label: 'Updated newest', tone: 'purple' },
    { value: 'updatedAsc', label: 'Updated oldest', tone: 'purple' },
    { value: 'createdDesc', label: 'Created newest', tone: 'purple' },
    { value: 'createdAsc', label: 'Created oldest', tone: 'purple' },
  ] satisfies DropdownOption<SortMode>[]
  const filteredChecklists = checklists
    .filter((checklist) => {
      const matchesStatus = statusFilter === 'all' || getChecklistStatus(checklist) === statusFilter
      const matchesOwner = ownerFilter === 'all' || checklist.user_id === ownerFilter
      const matchesSearch = checklist.title.toLowerCase().includes(normalizedSearchTerm)

      return matchesStatus && matchesOwner && matchesSearch
    })
  const sortedChecklists = [...filteredChecklists].sort((a, b) => {
      const updatedDiff = new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      const createdDiff = new Date(b.created_at).getTime() - new Date(a.created_at).getTime()

      if (sortMode === 'updatedAsc') return -updatedDiff
      if (sortMode === 'createdDesc') return createdDiff
      if (sortMode === 'createdAsc') return -createdDiff
      return updatedDiff
    })

  return (
    <>
    <TopBar onLogout={handleLogout} />
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Dashboard</h1>
          <p className={styles.subtitle}>
            Manage your checklist{totalChecklists === 1 ? '' : 's'} ({totalChecklists})
          </p>
        </div>

        <div className={styles.headerActions}>

          <Link to="/checklist/new" className={styles.newButton}>
            <FaPlus />
              New Checklist
          </Link>
        </div>
      </header>

      <section className={styles.overviewGrid}>
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
                onChange={setSelectedChecklistId}
                disabled={checklists.length === 0}
              />
            </div>
          </div>

          <div className={styles.statusContent}>
            <div className={styles.donut} style={donutStyle}>
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
            onClick={handleExportPdf}
            disabled={!selectedChecklist || isPreparingPdf}
          >
            {isPreparingPdf ? 'Preparing PDF...' : 'Create PDF'}
          </button>
        </div>

        <div className={`${styles.panel} ${styles.activityPanel}`}>
          <div className={styles.panelHeader}>
            <div>
              <h2 className={styles.panelTitle}>Recent Activity</h2>
              <p className={styles.panelSubtitle}>
                {activityLabelByMode[activityMode]} checklists over the last 7 days
              </p>
            </div>

            <div className={styles.segmentedControl} aria-label="Activity type">
              <button
                type="button"
                className={activityMode === 'created' ? styles.segmentActive : ''}
                onClick={() => setActivityMode('created')}
              >
                Created
              </button>
              <button
                type="button"
                className={activityMode === 'inProgress' ? styles.segmentActive : ''}
                onClick={() => setActivityMode('inProgress')}
              >
                In Progress
              </button>
              <button
                type="button"
                className={activityMode === 'completed' ? styles.segmentActive : ''}
                onClick={() => setActivityMode('completed')}
              >
                Completed
              </button>
            </div>
          </div>

          <div className={styles.chartShell}>
            <div className={styles.chartAxis} aria-hidden="true">
              {activityAxisLabels.map((label) => (
                <span key={label}>{label}</span>
              ))}
            </div>

            <div className={styles.chart}>
              {activityDays.map((day, index) => {
                const height = day.count === 0 ? 7 : Math.max(16, Math.round((day.count / maxActivityCount) * 100))

                return (
                  <div
                    className={styles.barGroup}
                    key={day.key}
                    title={`${day.count} checklist${day.count === 1 ? '' : 's'} ${activityLabelByMode[activityMode]}`}
                  >
                    <div
                      className={`${styles.bar} ${index === activityDays.length - 1 ? styles.activeBar : ''}`}
                      style={{ height: `${height}px` }}
                      aria-label={`${day.count} checklist${day.count === 1 ? '' : 's'} ${activityLabelByMode[activityMode]} on ${day.label}`}
                    />
                    <span>{day.label}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </section>

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

              <CustomDropdown
                label="Filter by owner"
                value={ownerFilter}
                options={ownerFilterOptions}
                onChange={setOwnerFilter}
              />

              <CustomDropdown
                label="Sort checklists"
                value={sortMode}
                options={sortOptions}
                onChange={setSortMode}
              />
            </div>
          </div>
        </div>

        {isLoading ? <p className={styles.message}>Loading checklists...</p> : null}
        {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}

        {!isLoading && !errorMessage && checklists.length === 0 ? (
          <div className={styles.emptyState}>
            <h3>No checklists yet</h3>
            <p>Create your first checklist to start managing inspections.</p>
            <Link to="/checklist/new" className={styles.openButton}>
              <FaPlus />
              New Checklist
            </Link>
          </div>
        ) : null}

        {!isLoading && !errorMessage && checklists.length > 0 && sortedChecklists.length === 0 ? (
          <div className={styles.emptyState}>
            <h3>No matching checklists</h3>
            <p>Try another name, status, owner, or sort option.</p>
          </div>
        ) : null}

        {!isLoading && !errorMessage && sortedChecklists.length > 0 ? (
          <div className={styles.cardGrid}>
            {sortedChecklists.map((checklist) => {
              const status = getChecklistStatus(checklist)
              const badgeClassName =
                status === 'Completed'
                  ? styles.completedBadge
                  : status === 'Not Started'
                    ? styles.notStartedBadge
                    : styles.progressBadge

              return (
                <article
                  key={checklist.id}
                  className={`${styles.card} ${selectedChecklistId === checklist.id ? styles.selectedCard : ''}`}
                >
                  <div className={styles.cardHeader}>
                    <h3>{checklist.title}</h3>
                    <span className={badgeClassName}>
                      {status}
                    </span>
                  </div>

                  <p className={styles.description}>
                    {checklist.description ?? 'No description.'}
                  </p>

                  <div className={styles.meta}>
                    <span>
                      <FaUser />
                      {getOwnerName(checklist.user_id)}
                    </span>

                    <span>
                      <FaCalendarAlt />
                      Updated {new Date(checklist.updated_at).toLocaleDateString()}
                    </span>
                  </div>

                  <p className={styles.items}>
                    {checklist.completed_items}/{checklist.total_items} items completed
                  </p>

                  <div className={styles.actions}>
                    <button
                      className={styles.statsButton}
                      type="button"
                      onClick={() => setSelectedChecklistId(checklist.id)}
                    >
                      View Stats
                    </button>

                    <Link
                      to={`/checklist/use/${checklist.id}`}
                      className={styles.useButton}
                    >
                      <FaPlay />
                      Use Checklist
                    </Link>

                    <Link
                      to={`/checklist/edit/${checklist.id}`}
                      className={styles.editButton}
                    >
                      <FaRegEdit />
                      Edit Checklist
                    </Link>

                    <button className={styles.iconButton} type="button" aria-label={`Delete ${checklist.title}`}>
                      <ImBin />
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        ) : null}
      </section>

      {pdfChecklist && selectedChecklist && pdfChecklistRoot ? (
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
      ) : null}
    </main>
    </>
  )
}

export default HomePage

function isChecklistRoot(value: unknown): value is ChecklistRoot {
  if (!value || typeof value !== 'object') return false

  const candidate = value as { type?: unknown; children?: unknown }
  return candidate.type === 'root' && Array.isArray(candidate.children)
}
