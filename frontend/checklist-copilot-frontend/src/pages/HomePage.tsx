import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import styles from '../page-styles/HomePage.module.css'
import { deleteChecklist, listChecklists } from '../api/checklist'
import { ApiError } from '../api/http'
import type { ChecklistSummary } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'

import {
  FaPlus,
  FaPlay,
  FaUser,
  FaCalendarAlt
} from 'react-icons/fa'

import { IoCheckmarkCircleOutline } from "react-icons/io5";
import { GoClock } from "react-icons/go";
import { CiFlag1 } from "react-icons/ci";
import { ImBin } from "react-icons/im";

import TopBar from '../components/TopBar'

function HomePage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const [checklists, setChecklists] = useState<ChecklistSummary[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  function handleLogout() {
    removeToken()
    navigate('/')
  }

  async function handleDelete(checklist: ChecklistSummary) {
    const label = checklist.title || 'this checklist'
    if (!window.confirm(`Delete "${label}"? This cannot be undone.`)) return
    try {
      await deleteChecklist(checklist.id)
      // Optimistic: drop it from the rendered list without refetching.
      setChecklists((prev) => prev.filter((c) => c.id !== checklist.id))
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Could not delete checklist.'
      window.alert(message)
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
        if (isMounted) setChecklists(response.checklists)
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

  // Derive status counts from the denormalized stats columns the backend keeps
  // in sync on every save.
  //   - completed:   every item completed (and at least one item exists)
  //   - inProgress:  some completed but not all
  //   - notStarted:  nothing completed yet (or the checklist is still empty)
  const completedCount = checklists.filter(
    (c) => c.total_items > 0 && c.completed_items === c.total_items,
  ).length
  const inProgressCount = checklists.filter(
    (c) => c.completed_items > 0 && c.completed_items < c.total_items,
  ).length
  const notStartedCount = totalChecklists - completedCount - inProgressCount

  function progressPercent(c: ChecklistSummary): number {
    if (c.total_items <= 0) return 0
    return Math.round((c.completed_items / c.total_items) * 100)
  }

  return (
    <>
    <TopBar onLogout={handleLogout} />
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Dashboard</h1>
          <p className={styles.subtitle}>Manage your inspection forms</p>
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
          <h2 className={styles.panelTitle}>Status Overview</h2>

          <div className={styles.statusContent}>
            <div className={styles.donut}>
              <span className={styles.donutNumber}>{totalChecklists}</span>
              <span className={styles.donutLabel}>total</span>
            </div>

            <div className={styles.statusList}>
              <div>
                <span className={styles.redDot}>
                  <CiFlag1 />
                </span>
                <span>Not Started</span>
                <strong>{notStartedCount}</strong>
              </div>
              <div>
                <span className={styles.yellowDot}>
                  <GoClock />
                </span>
                <span>In Progress</span>
                <strong>{inProgressCount}</strong>
              </div>
              <div>
                <span className={styles.greenDot}>
                  <IoCheckmarkCircleOutline />
                </span>
                <span>Completed</span>
                <strong>{completedCount}</strong>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Recent Activity</h2>

          <div className={styles.chart}>
            {['Fri', 'Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu'].map((day, index) => (
              <div className={styles.barGroup} key={day}>
                <div
                  className={`${styles.bar} ${day === 'Thu' ? styles.activeBar : ''}`}
                  style={{ height: `${[100, 7, 7, 17, 7, 7, 50][index]}px` }}
                />
                <span>{day}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.content}>
        <h2 className={styles.sectionTitle}>My Checklists</h2>

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

        {!isLoading && !errorMessage && checklists.length > 0 ? (
          <div className={styles.cardGrid}>
            {checklists.map((checklist) => {
              return (
                <article key={checklist.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>{checklist.title?.trim() || 'Untitled checklist'}</h3>
                    <span className={styles.progressBadge}>
                      Checklist
                    </span>
                  </div>

                  <p className={styles.description}>
                    {checklist.description ?? 'No description.'}
                  </p>

                  <div className={styles.meta}>
                    <span>
                      <FaUser />
                      Owner
                    </span>

                    <span>
                      <FaCalendarAlt />
                      Updated {new Date(checklist.updated_at).toLocaleDateString()}
                    </span>
                  </div>

                  {/* Inline progress: bar + numeric summary. Uses the
                      backend's denormalized stats so the dashboard never has
                      to load the heavy JSON column for these numbers. */}
                  <div className={styles.progressRow}>
                    <div className={styles.progressTrack} aria-hidden="true">
                      <div
                        className={styles.progressFill}
                        style={{ width: `${progressPercent(checklist)}%` }}
                      />
                    </div>
                    <span className={styles.progressLabel}>
                      {checklist.total_items > 0
                        ? `${checklist.completed_items}/${checklist.total_items} (${progressPercent(checklist)}%)`
                        : 'Empty'}
                    </span>
                  </div>

                  <div className={styles.actions}>
                    {/* Big "Open" → use mode (fill it out). Small flag →
                        edit mode (modify the structure). Inside either
                        page there's no mode toggle anymore — the dashboard
                        is where the user picks. */}
                    <Link to={`/checklist/use/${checklist.id}`} className={styles.openButton}>
                      <FaPlay />
                      Open
                    </Link>

                    <Link
                      to={`/checklist/edit/${checklist.id}`}
                      className={styles.iconButton}
                      title="Edit structure"
                      aria-label={`Edit ${checklist.title || 'checklist'}`}
                    >
                      <CiFlag1 />
                    </Link>

                    <button
                      className={styles.iconButton}
                      type="button"
                      onClick={() => handleDelete(checklist)}
                      title="Delete checklist"
                      aria-label={`Delete ${checklist.title || 'checklist'}`}
                    >
                      <ImBin />
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        ) : null}
      </section>
    </main>
    </>
  )
}

export default HomePage