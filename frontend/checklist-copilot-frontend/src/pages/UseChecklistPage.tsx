import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import styles from '../page-styles/UseChecklistPage.module.css'
import { getChecklistById } from '../api/checklist'
import type { Checklist } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import { ChecklistRenderer, mockChecklist } from '../checklist-components'
import type { ChecklistRoot } from '../checklist-components'
import { HiOutlineSparkles } from 'react-icons/hi2'
import TopBar from '../pages/TopBar'

function UseChecklistPage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const { checklist_id } = useParams<{ checklist_id: string }>()
  const [checklist, setChecklist] = useState<Checklist | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const missingChecklistId = isAuthorized && !checklist_id

  function handleLogout() {
    removeToken()
    navigate('/')
  }

  useEffect(() => {
    if (!isAuthorized || !checklist_id) {
      return
    }

    const checklistId = checklist_id

    let isMounted = true

    async function fetchChecklist() {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const response = await getChecklistById(checklistId as string)
        if (isMounted) {
          setChecklist(response)
        }
      } catch {
        if (isMounted) {
          setErrorMessage('Could not load checklist.')
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void fetchChecklist()

    return () => {
      isMounted = false
    }
  }, [checklist_id, isAuthorized])

  if (isCheckingAuth) {
    return (
      <main className={styles.page}>
        <section className={styles.content}>
          <p className={styles.message}>Checking session...</p>
        </section>
      </main>
    )
  }

  if (!isAuthorized) {
    return null
  }

  const renderedChecklist = isChecklistRoot(checklist?.checklist) ? checklist.checklist : mockChecklist

  return (
    <>
    <TopBar onLogout={handleLogout} />
    <main className={styles.page}>
      

      <button className={styles.aiButton} type="button" aria-label="Open AI assistant">
        <HiOutlineSparkles />
      </button>

      <section className={styles.content}>
        <header className={styles.checklistHeader}>
          <div>
            <p className={styles.status}>In Progress</p>
            <h1 className={styles.title}>{checklist?.title ?? 'Use Checklist'}</h1>
            <p className={styles.description}>
              {checklist?.description ?? 'Review each section and complete the required inspection fields.'}
            </p>
            <div className={styles.metaRow}>
              <span>{renderedChecklist.children.length} sections</span>
              {checklist ? <span>Creator {checklist.user_id}</span> : null}
              {checklist ? <span>Created {formatDate(checklist.created_at)}</span> : null}
              {checklist ? <span>Updated {formatDate(checklist.updated_at)}</span> : null}
              <span>Checklist ID {checklist_id ?? 'mock'}</span>
            </div>
          </div>

        </header>

        <div className={styles.progressHeader}>
          <span>Progress (%)</span>
          <span>33%</span>
        </div>
        <div className={styles.progressTrack} aria-hidden="true">
          <span className={styles.progressFill} />
        </div>

        {isLoading ? <p className={styles.message}>Loading checklist...</p> : null}
        {missingChecklistId ? <p className={styles.error}>Checklist ID is missing in URL.</p> : null}
        {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
        {!isLoading && !missingChecklistId && !errorMessage ? (
          <div className={styles.checklistShell}>
            <ChecklistRenderer checklist={renderedChecklist} />
          </div>
        ) : null}

        <Link to="/home" className={styles.backLink}>Back to Dashboard</Link>
      </section>
    </main>
    </>
  )
}

function isChecklistRoot(value: unknown): value is ChecklistRoot {
  if (!value || typeof value !== 'object') return false

  const candidate = value as { type?: unknown; children?: unknown }
  return candidate.type === 'root' && Array.isArray(candidate.children)
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

export default UseChecklistPage
