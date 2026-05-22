import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import styles from '../page-styles/HomePage.module.css'
import { listChecklists } from '../api/checklist'
import type { ChecklistSummary } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'

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
    if (!isAuthorized) {
      return
    }

    let isMounted = true

    async function fetchChecklists() {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const response = await listChecklists()
        if (isMounted) {
          setChecklists(response.checklists)
        }
      } catch {
        if (isMounted) {
          setErrorMessage('Could not load checklists.')
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
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
        <section className={styles.content}>
          <p className={styles.message}>Checking session...</p>
        </section>
      </main>
    )
  }

  if (!isAuthorized) {
    return null
  }

  return (
    <main className={styles.page}>
      <button className={styles.logoutButton} type='button' onClick={handleLogout}>
        Log out
      </button>

      <section className={styles.content}>
        <h1 className={styles.title}>Your Checklists</h1>

        {isLoading ? <p className={styles.message}>Loading checklists...</p> : null}
        {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}

        {!isLoading && !errorMessage && checklists.length === 0 ? (
          <p className={styles.message}>No checklists found.</p>
        ) : null}

        {!isLoading && !errorMessage && checklists.length > 0 ? (
          <ul className={styles.list}>
            {checklists.map((checklist) => (
              <li key={checklist.id} className={styles.listItem}>
                <div className={styles.itemMain}>
                  <h2 className={styles.itemTitle}>{checklist.title}</h2>
                  <p className={styles.itemDescription}>{checklist.description ?? 'No description.'}</p>
                  <p className={styles.itemMeta}>
                    Last updated: {new Date(checklist.updated_at).toLocaleString()}
                  </p>
                </div>
                <div className={styles.itemActions}>
                  <Link to={`/checklist/edit/${checklist.id}`} className={styles.actionButton}>
                    Edit
                  </Link>
                  <Link to={`/checklist/use/${checklist.id}`} className={styles.actionButtonSecondary}>
                    Use
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </main>
  )
}

export default HomePage
