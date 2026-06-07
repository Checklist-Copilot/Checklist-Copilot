import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  FiArrowLeft,
  FiCornerUpLeft,
  FiCornerUpRight,
  FiEye,
  FiSave,
  FiSend,
  FiUser,
} from 'react-icons/fi'
import {
  MdOutlineViewHeadline,
  MdOutlineCheckBox,
  MdOutlineChecklist,
  MdShortText,
  MdNumbers,
  MdOutlineImage,
  MdOutlineTableChart,
} from 'react-icons/md'

import AIPromptInput from '../components/AIPromptInput'
import { ChecklistRenderer } from '../checklist-components'
import type { ChecklistRoot } from '../checklist-components'
import { getChecklistById, updateChecklistMetadata } from '../api/checklist'
import { editChecklistWithAi } from '../api/ai'
import { removeToken } from '../auth/tokenStorage'
import { useRequireAuth } from '../hooks/useRequireAuth'
import { ApiError } from '../api/http'
import styles from '../page-styles/EditChecklistPage.module.css'

// Component palette items shown in the left toolbar in edit mode. Each one is
// a click-target the user will eventually drag into the checklist — for now
// the buttons are wired up only as visual placeholders (status: "soon").
const PALETTE: Array<{ type: string; label: string; icon: React.ReactNode }> = [
  { type: 'section', label: 'Section', icon: <MdOutlineViewHeadline /> },
  { type: 'checkboxGroup', label: 'Checkbox group', icon: <MdOutlineChecklist /> },
  { type: 'checkbox', label: 'Checkbox', icon: <MdOutlineCheckBox /> },
  { type: 'textField', label: 'Text field', icon: <MdShortText /> },
  { type: 'numberField', label: 'Number field', icon: <MdNumbers /> },
  { type: 'imageBlock', label: 'Image block', icon: <MdOutlineImage /> },
  { type: 'table', label: 'Table', icon: <MdOutlineTableChart /> },
]

type ChatMessage = {
  id: number
  sender: 'user' | 'ai'
  text: string
}

function EditChecklistPage() {
  const navigate = useNavigate()
  const { isCheckingAuth, isAuthorized } = useRequireAuth()
  const { checklist_id } = useParams<{ checklist_id: string }>()

  const [title, setTitle] = useState<string>('Untitled checklist')
  // Mirror of the last value successfully persisted to the backend; lets us
  // detect "user actually changed the title" without firing PATCH on every blur.
  const [savedTitle, setSavedTitle] = useState<string>('Untitled checklist')
  const [tree, setTree] = useState<ChecklistRoot | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // AI assistant chat state.
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      sender: 'ai',
      text: 'Hi — describe the change you want and I’ll apply it.',
    },
  ])
  const [chatInput, setChatInput] = useState('')
  const [chatAttachments, setChatAttachments] = useState<File[]>([])
  const [isAiBusy, setIsAiBusy] = useState(false)

  function handleLogout() {
    removeToken()
    navigate('/')
  }

  useEffect(() => {
    if (!isAuthorized || !checklist_id) return
    let mounted = true

    async function load() {
      setIsLoading(true)
      setErrorMessage(null)
      try {
        const data = await getChecklistById(checklist_id as string)
        if (!mounted) return
        const loadedTitle = data.title || 'Untitled checklist'
        setTitle(loadedTitle)
        setSavedTitle(loadedTitle)
        setTree(data.checklist as unknown as ChecklistRoot)
      } catch {
        if (mounted) setErrorMessage('Could not load checklist.')
      } finally {
        if (mounted) setIsLoading(false)
      }
    }
    void load()
    return () => {
      mounted = false
    }
  }, [checklist_id, isAuthorized])

  async function handleTitleBlur() {
    if (!checklist_id) return
    const trimmed = title.trim()
    if (!trimmed) {
      // Revert to the previously saved title rather than persisting an empty one.
      setTitle(savedTitle)
      return
    }
    if (trimmed === savedTitle) return
    try {
      const updated = await updateChecklistMetadata(checklist_id, { title: trimmed })
      const newTitle = updated.title || trimmed
      setSavedTitle(newTitle)
      setTitle(newTitle)
    } catch (error) {
      // eslint-disable-next-line no-console
      console.warn('Could not save title', error)
      // Optimistic revert so the UI doesn't show an unsaved title.
      setTitle(savedTitle)
    }
  }

  async function handleAiSubmit() {
    if (!chatInput.trim() || !checklist_id || isAiBusy) return
    const instruction = chatInput.trim()
    setChatInput('')
    setIsAiBusy(true)
    setChatMessages((prev) => [
      ...prev,
      { id: Date.now(), sender: 'user', text: instruction },
    ])
    try {
      const result = await editChecklistWithAi(checklist_id, instruction)
      setTree(result.checklist as unknown as ChecklistRoot)
      // Backend may have updated the title/description via the AI's
      // `update_checklist_metadata` tool — reflect that in the top bar
      // input so the user sees the rename immediately.
      if (result.title) {
        setTitle(result.title)
        setSavedTitle(result.title)
      }
      setChatMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'ai',
          text: result.reply || 'Done.',
        },
      ])
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Could not apply that change.'
      setChatMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, sender: 'ai', text: message },
      ])
    } finally {
      setIsAiBusy(false)
    }
  }

  if (isCheckingAuth) {
    return (
      <main className={styles.page}>
        <p className={styles.message}>Checking session…</p>
      </main>
    )
  }
  if (!isAuthorized) return null

  return (
    <main className={styles.page}>
      {/* ===================== TOP BAR ====================== */}
      <header className={styles.topbar}>
        <div className={styles.topLeft}>
          <button
            type="button"
            className={styles.iconBtn}
            title="Back to dashboard"
            onClick={() => navigate('/home')}
          >
            <FiArrowLeft />
          </button>

          <input
            className={styles.titleInput}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={handleTitleBlur}
            onKeyDown={(e) => {
              if (e.key === 'Enter') e.currentTarget.blur()
            }}
            placeholder="Untitled checklist"
            title="Checklist title (edit to rename, blur or press Enter to save)"
          />
        </div>

        <div className={styles.topCenter}>
          {/* History controls — UI placeholders until the backend exposes
              undo/redo for in-progress edits. */}
          <button type="button" className={styles.iconBtn} title="Undo" disabled>
            <FiCornerUpLeft />
          </button>
          <button type="button" className={styles.iconBtn} title="Redo" disabled>
            <FiCornerUpRight />
          </button>
        </div>

        <div className={styles.topRight}>
          <button type="button" className={styles.textBtn} title="Preview" disabled>
            <FiEye /> Preview
          </button>
          <button type="button" className={styles.textBtn} title="Save" disabled>
            <FiSave /> Save
          </button>
          <button
            type="button"
            className={`${styles.textBtn} ${styles.publishBtn}`}
            title="Publish"
            disabled
          >
            <FiSend /> Publish
          </button>
          <button
            type="button"
            className={styles.accountBtn}
            title="Account"
            onClick={handleLogout}
            aria-label="Account"
          >
            <FiUser />
          </button>
        </div>
      </header>

      {/* ===================== BODY ========================= */}
      <div className={styles.body}>
        {/* ----- Left toolbar: component palette ----- */}
        <aside className={styles.leftPanel} aria-label="Component palette">
          <h3 className={styles.panelHeading}>Components</h3>
          <p className={styles.panelHint}>
            Drag (soon) or click an item to insert.
          </p>
          <div className={styles.paletteList}>
            {PALETTE.map((item) => (
              <button
                key={item.type}
                type="button"
                className={styles.paletteItem}
                title={`Add ${item.label}`}
                disabled
              >
                <span className={styles.paletteIcon}>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </aside>

        {/* ----- Middle: checklist canvas ----- */}
        <section className={styles.canvas} aria-label="Checklist preview">
          {isLoading ? <p className={styles.message}>Loading checklist…</p> : null}
          {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
          {tree ? (
            tree.children && tree.children.length > 0 ? (
              <div className={styles.canvasInner}>
                <ChecklistRenderer checklist={tree} />
              </div>
            ) : (
              <div className={styles.emptyState}>
                <h3 className={styles.emptyTitle}>This checklist is empty</h3>
                <p className={styles.emptyHint}>
                  Use the AI assistant on the right to describe what you want
                  the checklist to cover — sections, fields, and checkboxes
                  will be added automatically.
                </p>
                <p className={styles.emptyHint}>
                  Or pick a component from the palette on the left (coming
                  soon).
                </p>
              </div>
            )
          ) : !isLoading && !errorMessage ? (
            <p className={styles.message}>Checklist not loaded.</p>
          ) : null}
        </section>

        {/* ----- Right: AI assistant ----- */}
        <aside className={styles.rightPanel} aria-label="Assistant">
          <div className={styles.aiPanel}>
            <h3 className={styles.panelHeading}>Assistant</h3>
            <div className={styles.chatLog} aria-live="polite">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`${styles.chatBubble} ${
                    msg.sender === 'user' ? styles.chatBubbleUser : styles.chatBubbleAi
                  }`}
                >
                  {msg.text}
                </div>
              ))}
              {isAiBusy ? (
                <div className={`${styles.chatBubble} ${styles.chatBubbleAi}`}>
                  Thinking…
                </div>
              ) : null}
            </div>

            <AIPromptInput
              value={chatInput}
              onChange={setChatInput}
              onSubmit={handleAiSubmit}
              attachedFiles={chatAttachments}
              onAttachFiles={(files) =>
                setChatAttachments((prev) => [...prev, ...files])
              }
              onRemoveFile={(i) =>
                setChatAttachments((prev) => prev.filter((_, idx) => idx !== i))
              }
              accept="image/*,application/pdf"
              disabled={isAiBusy}
              placeholder="Ask Checkly to edit, or attach a photo…"
              submitLabel="Send"
            />
          </div>
        </aside>
      </div>
    </main>
  )
}

export default EditChecklistPage
