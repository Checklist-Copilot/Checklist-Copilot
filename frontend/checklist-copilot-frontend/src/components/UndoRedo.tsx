import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { FiArrowLeft, FiArrowRight, FiTrash2 } from 'react-icons/fi'
import { restoreChecklistJson } from '../api/checklist'
import type { Checklist } from '../types/checklist'
import type { ChecklistRoot } from '../checklist-components'
import undoRedoStyles from './UndoRedo.module.css'
import { ConfirmationModal } from './ConfirmationModal'

const INPUT_HISTORY_COMMIT_DELAY_MS = 900

export type UndoRedoHandle = {
  resetSessionHistory: (root: ChecklistRoot) => void
  recordSessionState: (root: ChecklistRoot) => void
  recordInputSequenceState: (root: ChecklistRoot) => void
  cancelPendingInputHistory: () => void
}

type UndoRedoProps = {
  checklistId?: string
  isSaving: boolean
  pendingCount: number
  clearQueue: () => void
  onServerChecklist: (checklist: Checklist) => void
  setEditableChecklist: (root: ChecklistRoot) => void
  setErrorMessage: (message: string | null) => void
  showToast: (message: string) => void
}

// Owns edit-session history for the checklist editor, including snapshot recording,
// undo/redo navigation, and reset confirmation. Parent components call the exposed
// methods when checklist edits happen, while this component renders the controls.
export const UndoRedo = forwardRef<UndoRedoHandle, UndoRedoProps>(function UndoRedo(
  {
    checklistId,
    isSaving,
    pendingCount,
    clearQueue,
    onServerChecklist,
    setEditableChecklist,
    setErrorMessage,
    showToast,
  },
  ref,
) {
  const [isResetSessionModalOpen, setIsResetSessionModalOpen] = useState(false)
  const [isApplyingSessionState, setIsApplyingSessionState] = useState(false)
  const [sessionHistory, setSessionHistory] = useState<ChecklistRoot[]>([])
  const [sessionIndex, setSessionIndex] = useState(0)
  const sessionHistoryRef = useRef<ChecklistRoot[]>([])
  const sessionIndexRef = useRef(0)
  const inputHistoryTimerRef = useRef<number | null>(null)
  const inputHistoryBaseIndexRef = useRef<number | null>(null)

  const canDiscardSession = sessionHistory.length > 1 || sessionIndex > 0
  const isSessionActionDisabled = isApplyingSessionState || isSaving || pendingCount > 0

  useEffect(() => {
    sessionHistoryRef.current = sessionHistory
  }, [sessionHistory])

  useEffect(() => {
    sessionIndexRef.current = sessionIndex
  }, [sessionIndex])

  useEffect(() => {
    return () => {
      if (inputHistoryTimerRef.current !== null) {
        window.clearTimeout(inputHistoryTimerRef.current)
      }
    }
  }, [])

  useImperativeHandle(ref, () => ({
    resetSessionHistory,
    recordSessionState,
    recordInputSequenceState,
    cancelPendingInputHistory,
  }))

  function cloneChecklistRoot(root: ChecklistRoot) {
    return JSON.parse(JSON.stringify(root)) as ChecklistRoot
  }

  function resetSessionHistory(root: ChecklistRoot) {
    const snapshot = cloneChecklistRoot(root)
    sessionHistoryRef.current = [snapshot]
    sessionIndexRef.current = 0
    setSessionHistory([snapshot])
    setSessionIndex(0)
  }

  function cancelPendingInputHistory() {
    if (inputHistoryTimerRef.current !== null) {
      window.clearTimeout(inputHistoryTimerRef.current)
      inputHistoryTimerRef.current = null
    }
    inputHistoryBaseIndexRef.current = null
  }

  function recordSessionState(root: ChecklistRoot) {
    cancelPendingInputHistory()
    const snapshot = cloneChecklistRoot(root)
    const nextHistory = [...sessionHistoryRef.current.slice(0, sessionIndexRef.current + 1), snapshot]
    const nextIndex = nextHistory.length - 1
    sessionHistoryRef.current = nextHistory
    sessionIndexRef.current = nextIndex
    setSessionHistory(nextHistory)
    setSessionIndex(nextIndex)
  }

  function recordInputSequenceState(root: ChecklistRoot) {
    const snapshot = cloneChecklistRoot(root)

    if (inputHistoryBaseIndexRef.current === null) {
      inputHistoryBaseIndexRef.current = sessionIndexRef.current
    }

    if (inputHistoryTimerRef.current !== null) {
      window.clearTimeout(inputHistoryTimerRef.current)
    }

    inputHistoryTimerRef.current = window.setTimeout(() => {
      const baseIndex = inputHistoryBaseIndexRef.current ?? sessionIndexRef.current
      const nextHistory = [...sessionHistoryRef.current.slice(0, baseIndex + 1), snapshot]
      const nextIndex = nextHistory.length - 1

      sessionHistoryRef.current = nextHistory
      sessionIndexRef.current = nextIndex
      setSessionHistory(nextHistory)
      setSessionIndex(nextIndex)

      inputHistoryTimerRef.current = null
      inputHistoryBaseIndexRef.current = null
    }, INPUT_HISTORY_COMMIT_DELAY_MS)
  }

  async function applySessionState(root: ChecklistRoot) {
    if (!checklistId || isSessionActionDisabled) return

    const snapshot = cloneChecklistRoot(root)
    setIsApplyingSessionState(true)
    setErrorMessage(null)
    cancelPendingInputHistory()
    clearQueue()
    setEditableChecklist(snapshot)

    try {
      const response = await restoreChecklistJson(checklistId, snapshot as unknown as Record<string, unknown>)
      onServerChecklist(response)
    } catch {
      setErrorMessage('Could not restore that checklist version.')
    } finally {
      setIsApplyingSessionState(false)
    }
  }

  function handleStepSessionHistory(direction: -1 | 1) {
    const nextIndex = sessionIndex + direction
    const snapshot = sessionHistory[nextIndex]
    if (!snapshot) {
      showToast(direction < 0 ? 'No earlier change in this edit session.' : 'No later change in this edit session.')
      return
    }

    setSessionIndex(nextIndex)
    void applySessionState(snapshot)
  }

  function handleRequestResetSession() {
    if (!canDiscardSession) {
      showToast('No session changes to reset.')
      return
    }

    setIsResetSessionModalOpen(true)
  }

  function handleDiscardSessionChanges() {
    const initialSnapshot = sessionHistory[0]
    if (!initialSnapshot) return

    setIsResetSessionModalOpen(false)
    cancelPendingInputHistory()
    resetSessionHistory(initialSnapshot)
    void applySessionState(initialSnapshot)
  }

  return (
    <div className={undoRedoStyles.historySection}>
      <div className={undoRedoStyles.historyHeader}>
        <p className={undoRedoStyles.historyTitle}>Edit Session</p>
        <p className={undoRedoStyles.historyHint}>Step through changes from this session.</p>
      </div>

      <div className={undoRedoStyles.historyButtons}>
        <button
          className={undoRedoStyles.historyButton}
          type="button"
          aria-label="Previous edit state"
          onClick={() => handleStepSessionHistory(-1)}
          disabled={isSessionActionDisabled}
        >
          <FiArrowLeft />
        </button>
        <button
          className={undoRedoStyles.historyButton}
          type="button"
          aria-label="Next edit state"
          onClick={() => handleStepSessionHistory(1)}
          disabled={isSessionActionDisabled}
        >
          <FiArrowRight />
        </button>
      </div>

      <button
        className={undoRedoStyles.discardSessionButton}
        type="button"
        onClick={handleRequestResetSession}
        disabled={isSessionActionDisabled}
      >
        <FiTrash2 />
        Reset
      </button>

      <ConfirmationModal
        isOpen={isResetSessionModalOpen}
        title="Reset this edit session?"
        message="This restores the checklist to the version from when you opened this edit page. Changes from this edit session will be permanently removed."
        confirmLabel="Reset"
        workingLabel="Resetting..."
        kicker="Edit session"
        tone="danger"
        isConfirming={isApplyingSessionState}
        onConfirm={handleDiscardSessionChanges}
        onClose={() => setIsResetSessionModalOpen(false)}
      />
    </div>
  )
})
