import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useRequireAuth } from '../hooks/useRequireAuth'
import { ApiError } from '../api/http'
import { createChecklist } from '../api/checklist'
import styles from '../page-styles/NewChecklistPage.module.css'

// Clicking "New Checklist" from the dashboard immediately creates an empty
// checklist on the backend and redirects to the edit workspace. The AI
// assistant on the edit page is the new entry point for generating content.

const EMPTY_CHECKLIST = { id: 'root', type: 'root', children: [] as unknown[] }

// Module-level guard against React 18 StrictMode mounting the component
// twice in dev. A per-instance `useRef` does NOT survive unmount-then-remount,
// so without this flag two checklists get created on every visit. Module-level
// state stays alive across mounts within the same page load; on full page
// reload it resets, which is what we want.
let isBootstrapping = false

function NewChecklistPage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthorized) return
    if (isBootstrapping) return
    isBootstrapping = true

    let cancelled = false
    async function bootstrap() {
      try {
        const created = await createChecklist({
          title: 'Untitled checklist',
          description: null,
          checklist: EMPTY_CHECKLIST,
        })
        if (cancelled) return
        navigate(`/checklist/edit/${created.id}`, { replace: true })
      } catch (error) {
        if (cancelled) return
        const message =
          error instanceof ApiError
            ? error.message
            : 'Could not create checklist.'
        setErrorMessage(message)
      } finally {
        // Reset so the next visit to /checklist/new starts fresh.
        isBootstrapping = false
      }
    }
    void bootstrap()
    return () => {
      cancelled = true
    }
  }, [isAuthorized, navigate])

  if (isCheckingAuth || !isAuthorized) {
    return null
  }

  return (
    <main className={styles.page}>
      {errorMessage ? (
        <div className={styles.errorBox}>
          <p className={styles.errorTitle}>Could not create a new checklist.</p>
          <p className={styles.errorMessage}>{errorMessage}</p>
          <button
            type="button"
            className={styles.retryButton}
            onClick={() => navigate('/home')}
          >
            Back to dashboard
          </button>
        </div>
      ) : (
        <div className={styles.spinnerBox}>
          <div className={styles.spinner} aria-hidden="true" />
          <p className={styles.spinnerLabel}>Creating a new checklist…</p>
        </div>
      )}
    </main>
  )
}

export default NewChecklistPage
