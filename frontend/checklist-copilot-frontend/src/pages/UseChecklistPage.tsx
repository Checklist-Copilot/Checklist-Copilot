import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import styles from '../page-styles/UseChecklistPage.module.css'
import { editChecklistWithAi, observeChecklistImages } from '../api/ai'
import { getChecklistById } from '../api/checklist'
import { CHECKLIST_FILES_CHANGED_EVENT } from '../api/files'
import type { Checklist } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import { useChecklistAutosave } from '../hooks/useChecklistAutosave'
import { ChecklistRenderer, mockChecklist } from '../checklist-components'
import type { ChecklistRoot } from '../checklist-components'
import { removeImageFileReferencesFromRoot, updateComponentInRoot } from '../checklist-components/treeUtils'
import { HiOutlineSparkles } from 'react-icons/hi2'
import TopBar from '../components/TopBar'
import AIChatPopup from '../components/AIChatPopup'
import type { ChatMessage } from '../components/AIChatPopup'
import { ChecklistContextFiles } from '../components/ChecklistContextFiles'
import { uploadChecklistImage } from '../api/files'

function UseChecklistPage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const { checklist_id } = useParams<{ checklist_id: string }>()
  const [checklist, setChecklist] = useState<Checklist | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isAIChatOpen, setIsAIChatOpen] = useState(false)
  const [aiMessages, setAiMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      sender: 'checkly',
      text: 'Hi, I am Checkly. How can I help you with this checklist?',
    },
  ])

  const missingChecklistId = isAuthorized && !checklist_id

  const acceptServerChecklist = useCallback((response: Checklist) => {
    setChecklist(response)
  }, [])

  const { enqueueOperation, clearQueue, pendingCount, isSaving, autosaveError } = useChecklistAutosave({
    checklistId: checklist_id,
    onServerChecklist: acceptServerChecklist,
  })

  function handleLogout() {
    removeToken()
    navigate('/')
  }

  function handleComponentUpdate(componentId: string, patch: Record<string, unknown>) {
    setChecklist((currentChecklist) => {
      if (!currentChecklist || !isChecklistRoot(currentChecklist.checklist)) return currentChecklist

      return {
        ...currentChecklist,
        checklist: updateComponentInRoot(currentChecklist.checklist, componentId, patch) as unknown as Record<string, unknown>,
      }
    })

    enqueueOperation({ operation: 'updateComponent', targetId: componentId, patch })
  }

  async function handleAiMessage(message: string, conversation: ChatMessage[], images: File[] = []) {
    if (!checklist_id) throw new Error('Checklist ID is missing.')

    const response = images.length > 0
      ? await observeChecklistImages(checklist_id, {
          instruction: message,
          image_ids: (await Promise.all(images.map((image) => uploadChecklistImage(checklist_id, image)))).map((file) => file.id),
          mode: 'use',
          prior_messages: buildAiPriorMessages(conversation),
        })
      : await editChecklistWithAi(checklist_id, buildAiInstruction(message, conversation), 'use')

    setChecklist((currentChecklist) => {
      if (!currentChecklist) return currentChecklist

      return {
        ...currentChecklist,
        checklist: response.checklist,
        checklist_prev: currentChecklist.checklist,
        updated_at: new Date().toISOString(),
      }
    })

    clearQueue()
    return response.reply
  }

  useEffect(() => {
    if (!isAuthorized || !checklist_id) return

    const checklistId = checklist_id
    let isMounted = true

    async function fetchChecklist() {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const response = await getChecklistById(checklistId)
        if (isMounted) setChecklist(response)
      } catch {
        if (isMounted) setErrorMessage('Could not load checklist.')
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    void fetchChecklist()

    return () => {
      isMounted = false
    }
  }, [checklist_id, isAuthorized])

  useEffect(() => {
    function handleContextImageDeleted(event: Event) {
      const { checklistId, deletedFileId } = (event as CustomEvent<{ checklistId?: string; deletedFileId?: string }>).detail ?? {}
      if (checklistId !== checklist_id || !deletedFileId || !isChecklistRoot(checklist?.checklist)) return

      const { root, removals } = removeImageFileReferencesFromRoot(checklist.checklist, deletedFileId)
      if (removals.length === 0) return

      setChecklist((currentChecklist) =>
        currentChecklist
          ? { ...currentChecklist, checklist: root as unknown as Record<string, unknown> }
          : currentChecklist,
      )
      removals.forEach(({ componentId, images }) => {
        enqueueOperation({ operation: 'updateComponent', targetId: componentId, patch: { images } })
      })
    }

    window.addEventListener(CHECKLIST_FILES_CHANGED_EVENT, handleContextImageDeleted)
    return () => window.removeEventListener(CHECKLIST_FILES_CHANGED_EVENT, handleContextImageDeleted)
  }, [checklist, checklist_id, enqueueOperation])

  if (isCheckingAuth) {
    return (
      <main className={styles.page}>
        <section className={styles.content}>
          <p className={styles.message}>Checking session...</p>
        </section>
      </main>
    )
  }

  if (!isAuthorized) return null

  const renderedChecklist = isChecklistRoot(checklist?.checklist) ? checklist.checklist : mockChecklist

  return (
    <>
      <TopBar onLogout={handleLogout} />

      <main className={styles.page}>
        <button
          className={styles.aiButton}
          type="button"
          aria-label="Open AI assistant"
          onClick={() => setIsAIChatOpen(true)}
        >
          <HiOutlineSparkles />
        </button>

        <AIChatPopup
          isOpen={isAIChatOpen}
          messages={aiMessages}
          setMessages={setAiMessages}
          onClose={() => setIsAIChatOpen(false)}
          onSendMessage={handleAiMessage}
        />

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

            <SaveStatus isSaving={isSaving} pendingCount={pendingCount} />
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
          {autosaveError ? <p className={styles.error}>{autosaveError}</p> : null}

          <ChecklistContextFiles checklistId={checklist_id} />

          {!isLoading && !missingChecklistId && !errorMessage ? (
            <div className={styles.checklistShell}>
              <ChecklistRenderer
                checklist={renderedChecklist}
                checklistId={checklist_id}
                onComponentUpdate={handleComponentUpdate}
              />
            </div>
          ) : null}

          <Link to="/home" className={styles.backLink}>
            Back to Dashboard
          </Link>
        </section>
      </main>
    </>
  )
}

function SaveStatus({ isSaving, pendingCount }: { isSaving: boolean; pendingCount: number }) {
  if (!isSaving && pendingCount === 0) return null

  return (
    <div className={styles.saveStatus} role="status" aria-live="polite">
      <span className={isSaving ? styles.savingDot : styles.pendingDot} />
      {isSaving ? 'Saving...' : 'Changes pending'}
    </div>
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

function buildAiPriorMessages(conversation: ChatMessage[]) {
  return conversation.slice(1, -1).map((chatMessage) => ({
    role: chatMessage.sender === 'user' ? 'user' as const : 'assistant' as const,
    content: chatMessage.text,
  }))
}

function buildAiInstruction(message: string, conversation: ChatMessage[]) {
  const priorMessages = conversation
    .slice(1, -1)
    .map((chatMessage) => `${chatMessage.sender === 'user' ? 'User' : 'Checkly'}: ${chatMessage.text}`)
    .join('\n\n')

  if (!priorMessages) return message

  return `Conversation so far:\n\n${priorMessages}\n\nCurrent user instruction:\n${message}`
}

export default UseChecklistPage
