import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { FiPlus, FiSave } from 'react-icons/fi'
import { HiOutlineSparkles } from 'react-icons/hi2'
import styles from '../page-styles/UseChecklistPage.module.css'
import {
  getChecklistById,
  updateChecklistById,
  type ChecklistOperation,
} from '../api/checklist'
import { editChecklistWithAi } from '../api/ai'
import type { Checklist } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import { ChecklistRenderer, mockChecklist } from '../checklist-components'
import type { ChecklistComponent, ChecklistRoot } from '../checklist-components'
import TopBar from '../components/TopBar'
import AIChatPopup from '../components/AIChatPopup'

const componentOptions = [
  { label: 'Section', type: 'section' },
  { label: 'Text Field', type: 'textField' },
  { label: 'Number Field', type: 'numberField' },
  { label: 'Checkbox Group', type: 'checkboxGroup' },
  { label: 'Image Block', type: 'imageBlock' },
  { label: 'Table', type: 'table' },
] as const

function EditChecklistPage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const { checklist_id } = useParams<{ checklist_id: string }>()

  const [checklist, setChecklist] = useState<Checklist | null>(null)
  const [editableChecklist, setEditableChecklist] = useState<ChecklistRoot>(mockChecklist)
  const [pendingOperations, setPendingOperations] = useState<ChecklistOperation[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isAIChatOpen, setIsAIChatOpen] = useState(false)
  const [focusedComponentId, setFocusedComponentId] = useState<string>('root')
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const missingChecklistId = isAuthorized && !checklist_id

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
      showToast('Add a section first before adding this component.')
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
    findComponentById(editableChecklist, targetContainerId)?.type === 'checkboxGroup'
      ? createComponent('checkbox')
      : createComponent(type)

  if (targetContainerId === 'root') {
    setEditableChecklist((current) => ({
      ...current,
      children: [...current.children, newComponent],
    }))
  } else {
    setEditableChecklist((current) => ({
      ...current,
      children: current.children.map((component) => {
        if (component.type === 'section' && component.id === targetContainerId) {
          return {
            ...component,
            children: [...component.children, newComponent],
          }
        }

        if (
          (component.type === 'checkboxGroup' || component.type === 'checkboxContainer') &&
          component.id === targetContainerId &&
          (newComponent.type === 'checkbox' || newComponent.type === 'checkboxItem')
        ) {
          return {
            ...component,
            items: [...component.items, newComponent],
          }
        }

        return component
      }),
    }))
  }

  setPendingOperations((current) => [
    ...current,
    {
      operation: 'addComponent',
      targetContainerId,
      position: 'end',
      component: newComponent as unknown as Record<string, unknown>,
    },
  ])

  setFocusedComponentId(newComponent.id)
  setSuccessMessage(null)
}

  function handleDeleteComponent(componentId: string) {
  setEditableChecklist((current) => ({
    ...current,
    children: current.children
      .filter((component) => component.id !== componentId)
      .map((component) => {
        if (component.type !== 'section') {
          return component
        }

        return {
          ...component,
          children: component.children.filter((child) => child.id !== componentId),
        }
      }),
  }))

  setPendingOperations((current) => [
    ...current,
    {
      operation: 'deleteComponent',
      targetId: componentId,
    },
  ])

  setSuccessMessage(null)
}

  function handleSectionUpdate(sectionId: string, patch: Record<string, unknown>) {
  setEditableChecklist((current) => ({
    ...current,
    children: current.children.map((component) =>
      component.id === sectionId ? { ...component, ...patch } : component,
    ),
  }))

  setPendingOperations((current) => [
    ...current,
    {
      operation: 'updateComponent',
      targetId: sectionId,
      patch,
    },
  ])

  setSuccessMessage(null)
}

  async function handleSaveChecklist() {
    if (!checklist_id || pendingOperations.length === 0) return

    setIsSaving(true)
    setErrorMessage(null)
    setSuccessMessage(null)

    try {
      const response = await updateChecklistById(checklist_id, pendingOperations)
      setChecklist(response)

      if (isChecklistRoot(response.checklist)) {
        setEditableChecklist(response.checklist)
      }

      setPendingOperations([])
      setSuccessMessage('Checklist saved successfully.')
    } catch {
      setErrorMessage('Could not save checklist.')
    } finally {
      setIsSaving(false)
    }
  }

  async function handleAiMessage(message: string) {
    if (!checklist_id) {
      throw new Error('Checklist ID is missing.')
    }

    const response = await editChecklistWithAi(checklist_id, message)

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

    setPendingOperations([])
    setSuccessMessage('Checklist updated by AI.')

    return response.reply
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

              <button
                type="button"
                className={styles.saveButton}
                onClick={handleSaveChecklist}
                disabled={isSaving || pendingOperations.length === 0}
              >
                <FiSave />
                {isSaving ? 'Saving...' : 'Save'}
              </button>
            </header>

            {isLoading ? <p className={styles.message}>Loading checklist...</p> : null}
            {missingChecklistId ? <p className={styles.error}>Checklist ID is missing in URL.</p> : null}
            {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
            {successMessage ? <p className={styles.message}>{successMessage}</p> : null}

            {!isLoading && !missingChecklistId && !errorMessage ? (
              <div className={styles.checklistShell}>
                <ChecklistRenderer
                  checklist={editableChecklist}
                  isEditMode
                  focusedComponentId={focusedComponentId}
                  onFocusComponent={setFocusedComponentId}
                  onSectionUpdate={handleSectionUpdate}
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
          onClose={() => setIsAIChatOpen(false)}
          onSendMessage={handleAiMessage}
        />
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

export default EditChecklistPage