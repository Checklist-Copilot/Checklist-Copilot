import { useEffect } from 'react'
import { FiAlertTriangle, FiX } from 'react-icons/fi'
import styles from './ConfirmDeleteModal.module.css'

type ConfirmDeleteModalProps = {
  isOpen: boolean
  title: string
  message: string
  confirmLabel: string
  cancelLabel?: string
  isConfirming?: boolean
  onConfirm: () => void | Promise<void>
  onClose: () => void
}

// Presents destructive confirmations in the app's visual language instead of using browser dialogs.
// The component owns modal accessibility basics and delegates the actual deletion to its parent.
export function ConfirmDeleteModal({
  isOpen,
  title,
  message,
  confirmLabel,
  cancelLabel = 'Cancel',
  isConfirming = false,
  onConfirm,
  onClose,
}: ConfirmDeleteModalProps) {
  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isConfirming) onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isConfirming, isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className={styles.backdrop} role="presentation" onMouseDown={isConfirming ? undefined : onClose}>
      <section
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-delete-title"
        aria-describedby="confirm-delete-message"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button className={styles.closeButton} type="button" aria-label="Close confirmation" onClick={onClose} disabled={isConfirming}>
          <FiX />
        </button>

        <div className={styles.iconWrap} aria-hidden="true">
          <FiAlertTriangle />
        </div>

        <div className={styles.copy}>
          <p className={styles.kicker}>Confirm deletion</p>
          <h2 id="confirm-delete-title">{title}</h2>
          <p id="confirm-delete-message">{message}</p>
        </div>

        <div className={styles.actions}>
          <button className={styles.cancelButton} type="button" onClick={onClose} disabled={isConfirming}>
            {cancelLabel}
          </button>
          <button className={styles.confirmButton} type="button" onClick={onConfirm} disabled={isConfirming} autoFocus>
            {isConfirming ? 'Deleting...' : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  )
}
