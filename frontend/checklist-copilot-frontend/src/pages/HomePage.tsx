import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { FaPlus } from 'react-icons/fa'
import styles from '../page-styles/HomePage.module.css'
import { getChecklistById } from '../api/checklist'
import type { Checklist } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import TopBar from '../components/TopBar'
import { ChecklistList } from '../components/home/ChecklistList'
import { HomePrintReport } from '../components/home/HomePrintReport'
import { RecentActivityPanel } from '../components/home/RecentActivityPanel'
import { StatusOverviewPanel } from '../components/home/StatusOverviewPanel'
import type { ActivityMode } from '../components/home/types'
import { useHomeChecklists } from '../components/home/useHomeChecklists'

function HomePage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const { checklists, ownerNames, isLoading, errorMessage, setErrorMessage } = useHomeChecklists(isAuthorized)
  const [selectedChecklistId, setSelectedChecklistId] = useState('')
  const [activityMode, setActivityMode] = useState<ActivityMode>('created')
  const [pdfChecklist, setPdfChecklist] = useState<Checklist | null>(null)
  const [isPreparingPdf, setIsPreparingPdf] = useState(false)

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

  return (
    <>
      <TopBar onLogout={handleLogout} />
      <main className={styles.page}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Dashboard</h1>
          </div>

          <div className={styles.headerActions}>
            <Link to="/checklist/new" className={styles.newButton}>
              <FaPlus />
              New Checklist
            </Link>
          </div>
        </header>

        <section className={styles.overviewGrid}>
          <StatusOverviewPanel
            checklists={checklists}
            selectedChecklist={selectedChecklist}
            selectedChecklistId={selectedChecklistId}
            onSelectChecklist={setSelectedChecklistId}
            onExportPdf={handleExportPdf}
            isPreparingPdf={isPreparingPdf}
          />

          <RecentActivityPanel
            checklists={checklists}
            selectedChecklist={selectedChecklist}
            activityMode={activityMode}
            onActivityModeChange={setActivityMode}
          />
        </section>

        <ChecklistList
          checklists={checklists}
          selectedChecklistId={selectedChecklistId}
          ownerNames={ownerNames}
          isLoading={isLoading}
          errorMessage={errorMessage}
          onSelectChecklist={setSelectedChecklistId}
        />

        <HomePrintReport pdfChecklist={pdfChecklist} selectedChecklist={selectedChecklist} />
      </main>
    </>
  )
}

export default HomePage
