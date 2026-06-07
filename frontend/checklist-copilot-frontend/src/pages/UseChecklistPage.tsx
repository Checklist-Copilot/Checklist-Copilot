import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import styles from '../page-styles/UseChecklistPage.module.css'
import { editChecklistWithAi } from '../api/ai'
import { getChecklistById, patchChecklist } from '../api/checklist'
import type { ChecklistOperation } from '../api/checklist'
import type { Checklist } from '../types/checklist'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import { ChecklistRenderer, mockChecklist } from '../checklist-components'
import type { ChecklistRoot } from '../checklist-components'
import { HiOutlineSparkles } from 'react-icons/hi2'
import TopBar from '../components/TopBar'
import AIChatPopup from '../components/AIChatPopup'

function UseChecklistPage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const { checklist_id } = useParams<{ checklist_id: string }>()
  const [checklist, setChecklist] = useState<Checklist | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [checklistRenderVersion, setChecklistRenderVersion] = useState(0)
  const missingChecklistId = isAuthorized && !checklist_id
  const [isAIChatOpen, setIsAIChatOpen] = useState(false)
  // Surface save failures inline — invisible console.warn is no good for
  // someone testing the app.
  const [saveError, setSaveError] = useState<string | null>(null)

  // Kept up to date with the latest checklist for the event-delegation handler,
  // which captures its closure at effect-attach time. Without this ref the
  // handler would see a stale tree and look up component types incorrectly.
  const checklistRef = useRef<Checklist | null>(null)
  useEffect(() => {
    checklistRef.current = checklist
  }, [checklist])

  const canvasRef = useRef<HTMLDivElement | null>(null)

  function handleLogout() {
    removeToken()
    navigate('/')
  }

  // Sends the user's instruction to the backend so the AI can edit the current checklist.
  async function handleAiMessage(message: string) {
    if (!checklist_id) throw new Error('Checklist ID is missing.')

    const response = await editChecklistWithAi(checklist_id, message)
    setChecklist((current) => {
      if (!current) return current
      return {
        ...current,
        title: response.title || current.title,
        description: response.description ?? current.description,
        checklist: response.checklist,
        checklist_prev: current.checklist,
        updated_at: new Date().toISOString(),
      }
    })
    // Force the renderer to remount so uncontrolled inputs pick up new defaults.
    setChecklistRenderVersion((version) => version + 1)
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
        const response = await getChecklistById(checklistId as string)
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

  // ------------------------------------------------------------------- //
  // Save on input change — single delegated 'change' listener on the     //
  // wrapper div. The renderers use uncontrolled inputs and set           //
  // data-component-id on their containers, so we can walk up the DOM     //
  // from the changed input, look up the component's type in the local   //
  // tree, build the right patch shape, and PATCH the backend.            //
  //                                                                      //
  // NOTE: depend on `checklist` (not just checklist_id) so the effect    //
  // re-runs once the loaded data flips the canvas div into the DOM. The  //
  // earlier `[checklist_id]`-only dep meant the first render attached    //
  // nothing (canvas was null while isLoading=true) and the listener was  //
  // never re-attached — saves silently went into the void.               //
  // ------------------------------------------------------------------- //
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !checklist_id || !checklist) return

    async function onChange(event: Event) {
      const target = event.target
      if (!(target instanceof HTMLInputElement) && !(target instanceof HTMLTextAreaElement)) {
        return
      }

      // Find the nearest component container.
      let node: HTMLElement | null = target
      while (node && !node.dataset?.componentId) node = node.parentElement
      const componentId = node?.dataset?.componentId
      if (!componentId) return

      // Look up the component's type in the live tree (via ref so we're not stale).
      const tree = checklistRef.current?.checklist as ChecklistRoot | undefined
      const component = tree ? findComponentById(tree, componentId) : null
      if (!component) return

      let patch: Record<string, unknown> | null = null
      if (component.type === 'checkbox' && target instanceof HTMLInputElement && target.type === 'checkbox') {
        patch = { checked: target.checked }
      } else if (component.type === 'textField') {
        patch = { value: target.value }
      } else if (component.type === 'numberField' && target instanceof HTMLInputElement) {
        // Empty string means "cleared"; otherwise coerce. NaN guards against
        // invalid manual entries.
        const raw = target.value
        const parsed = raw === '' ? null : Number(raw)
        if (parsed !== null && Number.isNaN(parsed)) return
        patch = { value: parsed }
      }
      if (!patch) return

      const operation: ChecklistOperation = {
        operation: 'updateComponent',
        targetId: componentId,
        patch,
      }

      try {
        const updated = await patchChecklist(checklist_id as string, [operation])
        // Replace the row's state, but DO NOT bump checklistRenderVersion —
        // that would remount the renderer and reset the input the user just
        // edited. We only need the stats to refresh.
        setChecklist(updated)
        setSaveError(null)
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Could not save your change.'
        setSaveError(message)
        // eslint-disable-next-line no-console
        console.warn('Could not save change:', err)
      }
    }

    // Plain 'change' covers: checkboxes (toggle), text/textarea (blur/Enter),
    // and number inputs (blur/Enter). 'input' would fire on every keystroke
    // and spam the backend.
    canvas.addEventListener('change', onChange)
    return () => canvas.removeEventListener('change', onChange)
  }, [checklist_id, checklist])

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

  const renderedChecklist = isChecklistRoot(checklist?.checklist) ? checklist!.checklist : mockChecklist

  // Live progress derived from the row's denormalized stats columns. Recomputed
  // on every PATCH the backend handles, so this updates the moment a checkbox
  // ticks or a field gets filled.
  const completed = checklist?.completed_items ?? 0
  const total = checklist?.total_items ?? 0
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0

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
          onClose={() => setIsAIChatOpen(false)}
          onSendMessage={handleAiMessage}
        />

        <section className={styles.content}>
          <header className={styles.checklistHeader}>
            <div>
              <p className={styles.status}>
                {total === 0
                  ? 'Empty'
                  : completed === 0
                    ? 'Not started'
                    : completed === total
                      ? 'Completed'
                      : 'In Progress'}
              </p>
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

          {/* Live progress — replaces the hardcoded "33%". The bar's fill width
              is set inline so it overrides the static CSS rule. */}
          <div className={styles.progressHeader}>
            <span>Progress</span>
            <span>{total > 0 ? `${completed}/${total} (${percent}%)` : 'No items yet'}</span>
          </div>
          <div className={styles.progressTrack} aria-hidden="true">
            <span className={styles.progressFill} style={{ width: `${percent}%` }} />
          </div>

          {isLoading ? <p className={styles.message}>Loading checklist...</p> : null}
          {missingChecklistId ? <p className={styles.error}>Checklist ID is missing in URL.</p> : null}
          {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
          {saveError ? (
            <p className={styles.error}>Last change didn't save: {saveError}</p>
          ) : null}
          {!isLoading && !missingChecklistId && !errorMessage ? (
            <div className={styles.checklistShell} ref={canvasRef}>
              <ChecklistRenderer key={checklistRenderVersion} checklist={renderedChecklist} />
            </div>
          ) : null}

          <Link to="/home" className={styles.backLink}>Back to Dashboard</Link>
        </section>
      </main>
    </>
  )
}

// Walk the JSON tree looking for the component with this id. The renderers
// already set `data-component-id`, so we know it exists somewhere.
function findComponentById(node: unknown, id: string): { type?: string } | null {
  if (!node || typeof node !== 'object') return null
  const obj = node as { id?: unknown; type?: unknown; children?: unknown; items?: unknown }
  if (obj.id === id) return obj as { type?: string }
  for (const key of ['children', 'items'] as const) {
    const list = obj[key]
    if (Array.isArray(list)) {
      for (const child of list) {
        const hit = findComponentById(child, id)
        if (hit) return hit
      }
    }
  }
  return null
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
