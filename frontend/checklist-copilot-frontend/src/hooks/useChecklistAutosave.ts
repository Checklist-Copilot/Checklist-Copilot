import { useCallback, useEffect, useRef, useState } from 'react'
import { updateChecklistById, type ChecklistOperation } from '../api/checklist'
import type { Checklist } from '../types/checklist'

// How long we wait after the most recent local change before sending the
// queued operations to the backend. This keeps typing from producing one
// request per keystroke.
const AUTOSAVE_DELAY_MS = 1500

function mergeOperation(queue: ChecklistOperation[], next: ChecklistOperation) {
  // Repeated updates to the same component should collapse into one operation.
  // Example: typing "hello" in a text field should leave only the final
  // { value: "hello" } patch in the queue, not five separate patches.
  if (next.operation === 'updateComponent') {
    // If the component was created locally but has not been saved yet, merge
    // the patch into the queued add operation. The backend has not generated a
    // real id for it yet, so sending a separate update by temporary client id
    // would fail.
    const addIndex = queue.findIndex(
      (operation) =>
        operation.operation === 'addComponent' &&
        typeof operation.component.id === 'string' &&
        operation.component.id === next.targetId,
    )

    if (addIndex >= 0) {
      const addOperation = queue[addIndex]
      if (addOperation.operation === 'addComponent') {
        queue[addIndex] = {
          ...addOperation,
          component: { ...addOperation.component, ...next.patch },
        }
      }
      return queue
    }

    // If there is already an update for this persisted component, merge the
    // patches. Later keys win, which is exactly what we want for inputs.
    const updateIndex = queue.findIndex(
      (operation) => operation.operation === 'updateComponent' && operation.targetId === next.targetId,
    )

    if (updateIndex >= 0) {
      const updateOperation = queue[updateIndex]
      if (updateOperation.operation === 'updateComponent') {
        queue[updateIndex] = {
          ...updateOperation,
          patch: { ...updateOperation.patch, ...next.patch },
        }
      }
      return queue
    }
  }

  if (next.operation === 'deleteComponent') {
    // Add followed by delete before autosave means nothing needs to happen on
    // the backend. Remove the add and any local updates targeting that temp id.
    const addIndex = queue.findIndex(
      (operation) =>
        operation.operation === 'addComponent' &&
        typeof operation.component.id === 'string' &&
        operation.component.id === next.targetId,
    )

    if (addIndex >= 0) {
      queue.splice(addIndex, 1)
      return queue.filter(
        (operation) => operation.operation !== 'updateComponent' || operation.targetId !== next.targetId,
      )
    }

    // For persisted components, delete wins over any unsaved updates. There is
    // no point sending "update X" immediately before "delete X".
    return queue
      .filter((operation) => operation.operation !== 'updateComponent' || operation.targetId !== next.targetId)
      .concat(next)
  }

  // Add operations are appended. They may still absorb later updates above.
  return queue.concat(next)
}

type UseChecklistAutosaveOptions = {
  checklistId?: string
  // Called when it is safe to replace local UI state with the backend response.
  // We intentionally do not always call this immediately after a response,
  // because the user may have typed more changes while the request was in flight.
  onServerChecklist: (checklist: Checklist) => void
}

export function useChecklistAutosave({ checklistId, onServerChecklist }: UseChecklistAutosaveOptions) {
  // Refs are used for mutable autosave bookkeeping. Updating them does not
  // trigger rerenders, which is useful because the queue can change frequently
  // while the user types.
  const queueRef = useRef<ChecklistOperation[]>([])

  // Holds the latest backend response when we cannot apply it yet because newer
  // local operations are waiting in the queue.
  const latestServerChecklistRef = useRef<Checklist | null>(null)

  // The current debounce timer, if any.
  const timerRef = useRef<number | null>(null)

  // Small pieces of React state for UI feedback.
  const [pendingCount, setPendingCount] = useState(0)
  const [isSaving, setIsSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const syncPendingCount = useCallback(() => {
    setPendingCount(queueRef.current.length)
  }, [])

  const flush = useCallback(async () => {
    if (!checklistId || queueRef.current.length === 0) return

    // Move the current queue into an in-flight batch. New edits made while the
    // request is running will go into queueRef.current and must not be lost.
    const operations = queueRef.current
    queueRef.current = []
    syncPendingCount()
    setIsSaving(true)
    setErrorMessage(null)

    try {
      const response = await updateChecklistById(checklistId, operations)
      latestServerChecklistRef.current = response

      // Important edge case: addComponent uses a temporary client id in the UI,
      // but the backend generates the real id. If the user edits/deletes that
      // optimistic component while the add request is in flight, queued ops may
      // target a temp id that the backend will never know. Drop those ops and
      // accept the backend tree once the queue is clean.
      const addedClientIds = new Set(
        operations
          .filter((operation) => operation.operation === 'addComponent')
          .map((operation) => operation.component.id)
          .filter((id): id is string => typeof id === 'string'),
      )

      if (addedClientIds.size > 0) {
        queueRef.current = queueRef.current.filter((operation) => {
          if (operation.operation === 'updateComponent') return !addedClientIds.has(operation.targetId)
          if (operation.operation === 'deleteComponent') return !addedClientIds.has(operation.targetId)
          return true
        })
        syncPendingCount()
      }

      // Only replace local state with the server response if no newer local
      // edits are pending. This prevents stale responses from overwriting what
      // the user just typed while the request was in flight.
      if (queueRef.current.length === 0) {
        onServerChecklist(response)
        latestServerChecklistRef.current = null
      }
    } catch {
      // Put the failed batch back in front of any newer edits so a later flush
      // can retry everything in the original order.
      queueRef.current = [...operations, ...queueRef.current]
      syncPendingCount()
      setErrorMessage('Could not autosave checklist.')
    } finally {
      setIsSaving(false)
    }
  }, [checklistId, onServerChecklist, syncPendingCount])

  const scheduleFlush = useCallback(() => {
    // Standard debounce: every new edit resets the timer.
    if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(() => {
      timerRef.current = null
      void flush()
    }, AUTOSAVE_DELAY_MS)
  }, [flush])

  const enqueueOperation = useCallback(
    (operation: ChecklistOperation) => {
      // Copy before merge so callers do not accidentally share mutable queue
      // state with this hook.
      queueRef.current = mergeOperation([...queueRef.current], operation)
      syncPendingCount()
      scheduleFlush()
    },
    [scheduleFlush, syncPendingCount],
  )

  const clearQueue = useCallback(() => {
    // Used after AI edits or full reloads, where the local pending manual edits
    // should no longer be replayed.
    queueRef.current = []
    latestServerChecklistRef.current = null
    syncPendingCount()
    if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    timerRef.current = null
  }, [syncPendingCount])

  useEffect(() => {
    // If a server response was held back because local edits were pending, apply
    // it once saving finishes and the queue is empty.
    if (!isSaving && queueRef.current.length === 0 && latestServerChecklistRef.current) {
      onServerChecklist(latestServerChecklistRef.current)
      latestServerChecklistRef.current = null
    }
  }, [isSaving, onServerChecklist])

  useEffect(() => {
    // Clean up the debounce timer if the page unmounts.
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    }
  }, [])

  return { enqueueOperation, flush, clearQueue, pendingCount, isSaving, autosaveError: errorMessage }
}
