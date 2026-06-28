import { Link, useNavigate } from 'react-router-dom'
import { useCallback, useState } from 'react'
import { FaPlus } from 'react-icons/fa'
import styles from '../page-styles/HomePage.module.css'
import { deleteChecklist, getChecklistById } from '../api/checklist'
import type { Checklist } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import TopBar from '../components/TopBar'
import { ConfirmationModal } from '../components/ConfirmationModal'
import { ChecklistList } from '../components/home/ChecklistList'
import { HomePrintReport } from '../components/home/HomePrintReport'
import { RecentActivityPanel } from '../components/home/RecentActivityPanel'
import { StatusOverviewPanel } from '../components/home/StatusOverviewPanel'
import type { ActivityMode } from '../components/home/types'
import { useHomeChecklists } from '../components/home/useHomeChecklists'

function HomePage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const { checklists, setChecklists, ownerNames, isLoading, errorMessage, setErrorMessage } = useHomeChecklists(isAuthorized)
  const [selectedChecklistId, setSelectedChecklistId] = useState('')
  const [activityMode, setActivityMode] = useState<ActivityMode>('created')
  const [pdfChecklist, setPdfChecklist] = useState<Checklist | null>(null)
  const [isPreparingPdf, setIsPreparingPdf] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null)
  const [isDeletingChecklist, setIsDeletingChecklist] = useState(false)

  // Opens the custom confirmation modal with the checklist title for safer destructive action copy.
  function handleDeleteChecklist(id: string) {
    const checklist = checklists.find((item) => item.id === id)
    setDeleteTarget({ id, title: checklist?.title ?? 'this checklist' })
  }

  // Performs the checklist deletion after the modal confirms the user's intent.
  async function confirmDeleteChecklist() {
    if (!deleteTarget || isDeletingChecklist) return

    setIsDeletingChecklist(true)
    try {
      await deleteChecklist(deleteTarget.id)
      setChecklists((prev) => prev.filter((c) => c.id !== deleteTarget.id))
      if (selectedChecklistId === deleteTarget.id) setSelectedChecklistId('')
      setDeleteTarget(null)
    } catch {
      setErrorMessage('Could not delete checklist.')
    } finally {
      setIsDeletingChecklist(false)
    }
  }

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
    } catch {
      setErrorMessage('Could not prepare PDF.')
      setIsPreparingPdf(false)
    }
  }

  const handlePrintReportReady = useCallback(() => {
    if (!isPreparingPdf || !pdfChecklist) return

    window.print()
    setIsPreparingPdf(false)
  }, [isPreparingPdf, pdfChecklist])

  if (isCheckingAuth) {
    return (
      <main className={styles.page}>
        <p className={styles.message}>Checking session...</p>
      </main>
    )
  }

  if (!isAuthorized) return null

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
          onDelete={handleDeleteChecklist}
        />

        <HomePrintReport pdfChecklist={pdfChecklist} selectedChecklist={selectedChecklist} onReady={handlePrintReportReady} />
      </main>

      <ConfirmationModal
        isOpen={deleteTarget !== null}
        title={`Delete “${deleteTarget?.title ?? 'this checklist'}”?`}
        message="This removes the checklist and its linked context files. You cannot undo this action."
        confirmLabel="Delete checklist"
        isConfirming={isDeletingChecklist}
        onConfirm={confirmDeleteChecklist}
        onClose={() => setDeleteTarget(null)}
      />
    </>
  )
}

export default HomePage
