import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import styles from '../page-styles/EditChecklistPage.module.css'
import { getChecklistById } from '../api/checklist'
import type { Checklist } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'

function EditChecklistPage() {
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

  return (
    <main className={styles.page}>
      <button className={styles.logoutButton} type='button' onClick={handleLogout}>
        Log out
      </button>

      <section className={styles.content}>
        <h1 className={styles.title}>Edit Checklist</h1>
        {isLoading ? <p className={styles.message}>Loading checklist...</p> : null}
        {missingChecklistId ? <p className={styles.error}>Checklist ID is missing in URL.</p> : null}
        {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
        {!isLoading && !missingChecklistId && !errorMessage && checklist ? (
          <pre className={styles.json}>{JSON.stringify(checklist, null, 2)}</pre>
        ) : null}
      </section>
    </main>
  )
}

export default EditChecklistPage
