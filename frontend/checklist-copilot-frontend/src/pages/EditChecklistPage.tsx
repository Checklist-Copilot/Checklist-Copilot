import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { FiPlus } from 'react-icons/fi'
import { HiOutlineSparkles } from 'react-icons/hi2'
import styles from '../page-styles/UseChecklistPage.module.css'
import editStyles from '../page-styles/EditChecklistPage.module.css'
import { getChecklistById } from '../api/checklist'
import { editChecklistWithAi, reviewChecklistWithAi } from '../api/ai'
import type { Checklist } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import { useChecklistAutosave } from '../hooks/useChecklistAutosave'
import { ChecklistRenderer, mockChecklist } from '../checklist-components'
import type { ChecklistComponent, ChecklistRoot } from '../checklist-components'
import { addComponentToRoot, deleteComponentFromRoot, updateComponentInRoot } from '../checklist-components/treeUtils'
import TopBar from '../components/TopBar'
import AIChatPopup from '../components/AIChatPopup'
import type { ChatMessage } from '../components/AIChatPopup'
import { ConfirmationModal } from '../components/ConfirmationModal'
import { ChecklistContextFiles } from '../components/ChecklistContextFiles'

const componentOptions = [
  { label: 'Section', type: 'section' },
  { label: 'Text Field', type: 'textField' },
  { label: 'Number Field', type: 'numberField' },
  { label: 'Checkbox Group', type: 'checkboxGroup' },
  { label: 'Checkbox Item', type: 'checkbox' },
  { label: 'Image Block', type: 'imageBlock' },
  { label: 'Table', type: 'table' },
] as const

function EditChecklistPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const { checklist_id } = useParams<{ checklist_id: string }>()

  const [checklist, setChecklist] = useState<Checklist | null>(null)
  const [editableChecklist, setEditableChecklist] = useState<ChecklistRoot>(mockChecklist)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isAIChatOpen, setIsAIChatOpen] = useState(false)
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false)
  const [isReviewingChecklist, setIsReviewingChecklist] = useState(false)
  const [aiMessages, setAiMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      sender: 'checkly',
      text: 'Hi, I am Checkly. How can I help you with this checklist?',
    },
  ])
  const [focusedComponentId, setFocusedComponentId] = useState<string>('root')
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const missingChecklistId = isAuthorized && !checklist_id

  const acceptServerChecklist = useCallback((response: Checklist) => {
    setChecklist(response)
    if (isChecklistRoot(response.checklist)) setEditableChecklist(response.checklist)
  }, [])

  const { enqueueOperation, clearQueue, pendingCount, isSaving, autosaveError } = useChecklistAutosave({
    checklistId: checklist_id,
    onServerChecklist: acceptServerChecklist,
  })

  useEffect(() => {
    const warning = (location.state as { warning?: string } | null)?.warning
    if (warning) {
      showToast(warning)
      navigate(location.pathname, { replace: true, state: null })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleLogout() {
    removeToken()
    navigate('/')
  }

  function createId() {
    return crypto.randomUUID()
  }

  function showToast(message: string) {
  setToastMessage(message)

  window.setTimeout(() => {
    setToastMessage(null)
  }, 3200)
}

  function createComponent(type: ChecklistComponent['type']): ChecklistComponent {
    const id = createId()

    switch (type) {
      case 'section':
        return {
          id,
          humanReadableId: `section_${id}`,
          type: 'section',
          label: 'New Section',
          collapsed: false,
          children: [],
        }

      case 'textField':
        return {
          id,
          humanReadableId: `text_${id}`,
          type: 'textField',
          label: 'New Text Field',
          value: '',
          placeholder: 'Enter text',
          required: false,
          multiline: false,
        }

      case 'numberField':
        return {
          id,
          humanReadableId: `number_${id}`,
          type: 'numberField',
          label: 'New Number Field',
          value: null,
          unit: null,
          min: null,
          max: null,
          required: false,
        }

      case 'checkboxGroup':
        return {
          id,
          humanReadableId: `checkbox_group_${id}`,
          type: 'checkboxGroup',
          label: 'New Checkbox Group',
          items: [
            {
              id: createId(),
              humanReadableId: `checkbox_item_${id}`,
              type: 'checkbox',
              label: 'New checkbox item',
              checked: false,
              required: false,
            },
          ],
        }

      case 'checkbox':
      case 'checkboxItem':
        return {
          id,
          humanReadableId: `checkbox_item_${id}`,
          type: 'checkbox',
          label: 'New checkbox item',
          checked: false,
          required: false,
        }

      case 'imageBlock':
        return {
          id,
          humanReadableId: `image_block_${id}`,
          type: 'imageBlock',
          label: 'New Image Block',
          images: [],
          allowUpload: true,
        }

      case 'table': {
        const firstColumnId = createId()
        const secondColumnId = createId()

        return {
          id,
          humanReadableId: `table_${id}`,
          type: 'table',
          label: 'New Table',
          columns: [
            { id: firstColumnId, label: 'Column 1', type: 'text' },
            { id: secondColumnId, label: 'Column 2', type: 'text' },
          ],
          rows: [
            {
              id: createId(),
              cells: {
                [firstColumnId]: '',
                [secondColumnId]: '',
              },
            },
          ],
        }
      }

      default:
        return {
          id,
          humanReadableId: `text_${id}`,
          type: 'textField',
          label: 'New Text Field',
          value: '',
          placeholder: 'Enter text',
          required: false,
          multiline: false,
        }
    }
  }

  function findComponentById(root: ChecklistRoot, componentId: string): ChecklistComponent | ChecklistRoot | null {
    if (componentId === 'root') return root

    for (const component of root.children) {
      if (component.id === componentId) return component

      if (component.type === 'section') {
        const child = component.children.find((item) => item.id === componentId)
        if (child) return child
      }

      if (component.type === 'checkboxGroup' || component.type === 'checkboxContainer') {
        const item = component.items.find((checkbox) => checkbox.id === componentId)
        if (item) return item
      }
    }

    return null
  }

  function canContainComponent(
    target: ChecklistComponent | ChecklistRoot | null,
    newType: ChecklistComponent['type'],
  ) {
    if (!target) return false

    if (target.type === 'root') {
      return newType === 'section'
    }

    if (target.type === 'section') {
      return newType !== 'section' && newType !== 'checkbox' && newType !== 'checkboxItem'
    }

    if (target.type === 'checkboxGroup' || target.type === 'checkboxContainer') {
      return newType === 'checkbox' || newType === 'checkboxItem'
    }

    return false
  }

  function getFallbackTargetId(type: ChecklistComponent['type']) {
    if (type === 'section') return 'root'
    if (type === 'checkbox' || type === 'checkboxItem') return null

    const latestSection = [...editableChecklist.children]
      .reverse()
      .find((component) => component.type === 'section')

    return latestSection?.id ?? null
  }

  function handleAddComponent(type: ChecklistComponent['type']) {
  const selectedTarget = findComponentById(editableChecklist, focusedComponentId)
  let targetContainerId = focusedComponentId

  if (!canContainComponent(selectedTarget, type)) {
    const fallbackTargetId = getFallbackTargetId(type)

    if (!fallbackTargetId) {
      showToast(
        type === 'checkbox' || type === 'checkboxItem'
          ? 'Focus a checkbox group before adding a checkbox item.'
          : 'Add a section first before adding this component.',
      )
      return
    }

    targetContainerId = fallbackTargetId

    showToast(
      type === 'section'
        ? 'Sections are added to the checklist root.'
        : 'That component cannot contain children, so the new component was added to the latest section.',
    )
  }

  const newComponent =
    targetContainerId !== 'root' &&
    ['checkboxGroup', 'checkboxContainer'].includes(String(findComponentById(editableChecklist, targetContainerId)?.type))
      ? createComponent('checkbox')
      : createComponent(type)

  setEditableChecklist((current) => addComponentToRoot(current, targetContainerId, newComponent))

  enqueueOperation({
    operation: 'addComponent',
    targetContainerId,
    position: 'end',
    component: newComponent as unknown as { type: string; label: string } & Record<string, unknown>,
  })

  setFocusedComponentId(newComponent.id)
}

  function handleDeleteComponent(componentId: string) {
  setEditableChecklist((current) => deleteComponentFromRoot(current, componentId))
  enqueueOperation({ operation: 'deleteComponent', targetId: componentId })
}

  function handleComponentUpdate(componentId: string, patch: Record<string, unknown>) {
  setEditableChecklist((current) => updateComponentInRoot(current, componentId, patch))
  enqueueOperation({ operation: 'updateComponent', targetId: componentId, patch })
}

  // Sends chat instructions to the AI edit endpoint, including prior chat context so follow-up
  // requests like "apply your suggestions" can refer to an earlier AI review in the same session.
  async function handleAiMessage(message: string, conversation: ChatMessage[]) {
    if (!checklist_id) {
      throw new Error('Checklist ID is missing.')
    }

    const response = await editChecklistWithAi(checklist_id, buildAiInstruction(message, conversation))

    setChecklist((currentChecklist) => {
      if (!currentChecklist) return currentChecklist

      return {
        ...currentChecklist,
        checklist: response.checklist,
        checklist_prev: currentChecklist.checklist,
        updated_at: new Date().toISOString(),
      }
    })

    if (isChecklistRoot(response.checklist)) {
      setEditableChecklist(response.checklist)
    }

    clearQueue()

    return response.reply
  }

  // Opens the chat with a temporary review message, then swaps it for the backend review response.
  async function handleAiReview() {
    if (!checklist_id || isReviewingChecklist) return

    const reviewMessageId = Date.now()
    setIsReviewModalOpen(false)
    setIsAIChatOpen(true)
    setIsReviewingChecklist(true)
    setAiMessages((currentMessages) => [
      ...currentMessages,
      { id: reviewMessageId, sender: 'checkly', text: 'Generating review...' },
    ])

    try {
      const response = await reviewChecklistWithAi(checklist_id)
      setAiMessages((currentMessages) =>
        currentMessages.map((chatMessage) =>
          chatMessage.id === reviewMessageId
            ? { ...chatMessage, text: response.reply || 'I could not produce a review for this checklist.' }
            : chatMessage,
        ),
      )
    } catch {
      setAiMessages((currentMessages) =>
        currentMessages.map((chatMessage) =>
          chatMessage.id === reviewMessageId
            ? { ...chatMessage, text: 'I could not review this checklist. Please try again.' }
            : chatMessage,
        ),
      )
    } finally {
      setIsReviewingChecklist(false)
    }
  }

  useEffect(() => {
    if (!isAuthorized || !checklist_id) return

    let isMounted = true

    async function fetchChecklist() {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const response = await getChecklistById(checklist_id as string)

        if (isMounted) {
          setChecklist(response)
          setEditableChecklist(isChecklistRoot(response.checklist) ? response.checklist : mockChecklist)
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

  if (!isAuthorized) return null

  return (
    <>
      <TopBar onLogout={handleLogout} />

      <main className={styles.page}>
        <div className={styles.editLayout}>
          <aside className={styles.componentSidebar}>
            <p className={styles.sidebarTitle}>Components</p>
            <p className={styles.sidebarHint}>Click an item to insert it.</p>

            <div className={styles.componentList}>
              {componentOptions.map((option) => (
                <button
                  key={option.type}
                  type="button"
                  className={styles.componentItem}
                  onClick={() => handleAddComponent(option.type)}
                >
                  <FiPlus />
                  {option.label}
                </button>
              ))}
            </div>
          </aside>

          <section className={`${styles.content} ${styles.editContent}`}>
            <header className={styles.checklistHeader}>
              <div>
                <p className={styles.status}>Edit Mode</p>
                <h1 className={styles.title}>{checklist?.title ?? 'Edit Checklist'}</h1>
                <p className={styles.description}>
                  {checklist?.description ?? 'Add and delete checklist components manually.'}
                </p>

                <div className={styles.metaRow}>
                  <span>{editableChecklist.children.length} components</span>
                  {checklist ? <span>Creator {checklist.user_id}</span> : null}
                  {checklist ? <span>Created {formatDate(checklist.created_at)}</span> : null}
                  {checklist ? <span>Updated {formatDate(checklist.updated_at)}</span> : null}
                  <span>Checklist ID {checklist_id ?? 'mock'}</span>
                </div>
              </div>

              <div className={editStyles.headerTools}>
                <button
                  className={editStyles.aiReviewButton}
                  type="button"
                  onClick={() => setIsReviewModalOpen(true)}
                  disabled={isReviewingChecklist || isLoading || !checklist_id}
                >
                  <HiOutlineSparkles />
                  AI review
                </button>
                <SaveStatus isSaving={isSaving} pendingCount={pendingCount} />
              </div>
            </header>

            {isLoading ? <p className={styles.message}>Loading checklist...</p> : null}
            {missingChecklistId ? <p className={styles.error}>Checklist ID is missing in URL.</p> : null}
            {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
            {autosaveError ? <p className={styles.error}>{autosaveError}</p> : null}

            <ChecklistContextFiles checklistId={checklist_id} />

            {!isLoading && !missingChecklistId && !errorMessage ? (
              <div className={styles.checklistShell}>
                <ChecklistRenderer
                  checklist={editableChecklist}
                  checklistId={checklist_id}
                  isEditMode
                  focusedComponentId={focusedComponentId}
                  onFocusComponent={setFocusedComponentId}
                  onComponentUpdate={handleComponentUpdate}
                  onDeleteComponent={handleDeleteComponent}
                />
              </div>
            ) : null}

            <Link to="/home" className={styles.backLink}>
              Back to Dashboard
            </Link>
          </section>
        </div>

        {toastMessage ? (
        <div className={styles.toast} role="status" aria-live="polite">
          {toastMessage}
        </div>
      ) : null}

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

        <ConfirmationModal
          isOpen={isReviewModalOpen}
          title="Review checklist with AI?"
          message="Do you want to have this checklist reviewed by AI using its general knowledge about the topic, but also the related PDFs?"
          confirmLabel="Continue"
          workingLabel="Generating review..."
          kicker="AI review"
          tone="ai"
          isConfirming={isReviewingChecklist}
          onConfirm={handleAiReview}
          onClose={() => setIsReviewModalOpen(false)}
        />
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

function buildAiInstruction(message: string, conversation: ChatMessage[]) {
  const priorMessages = conversation
    .slice(1, -1)
    .map((chatMessage) => `${chatMessage.sender === 'user' ? 'User' : 'Checkly'}: ${chatMessage.text}`)
    .join('\n\n')

  if (!priorMessages) return message

  return `Conversation so far:\n\n${priorMessages}\n\nCurrent user instruction:\n${message}`
}

export default EditChecklistPage
