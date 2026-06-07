import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import styles from '../page-styles/HomePage.module.css'
import { listChecklists } from '../api/checklist'
import type { ChecklistSummary } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'

import {
  FaPlus,
  FaPlay,
  FaUser,
  FaCalendarAlt
} from 'react-icons/fa'
import { FaRegEdit } from 'react-icons/fa'

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
                <strong>0</strong>
              </div>
              <div>
                <span className={styles.yellowDot}>
                  <GoClock />
                </span>
                <span>In Progress</span>
                <strong>0</strong>
              </div>
              <div>
                <span className={styles.greenDot}>
                  <IoCheckmarkCircleOutline />
                </span>
                <span>Completed</span>
                <strong>{totalChecklists}</strong>
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
                    <h3>{checklist.title}</h3>
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

                  <p className={styles.items}>Ready to open</p>

                  <div className={styles.actions}>
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

                    <button className={styles.iconButton} type="button">
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