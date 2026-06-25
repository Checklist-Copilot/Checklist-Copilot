import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { FiAlertTriangle, FiX } from 'react-icons/fi'
import { HiOutlineSparkles } from 'react-icons/hi2'
import styles from './ConfirmationModal.module.css'

type ConfirmationModalProps = {
  isOpen: boolean
  title: string
  message: string
  confirmLabel: string
  cancelLabel?: string
  workingLabel?: string
  kicker?: string
  tone?: 'danger' | 'ai'
  isConfirming?: boolean
  onConfirm: () => void | Promise<void>
  onClose: () => void
}

// Presents destructive confirmations in the app's visual language instead of using browser dialogs.
// The component owns modal accessibility basics and delegates the actual deletion to its parent.
export function ConfirmationModal({
  isOpen,
  title,
  message,
  confirmLabel,
  cancelLabel = 'Cancel',
  workingLabel = 'Deleting...',
  kicker = 'Confirm deletion',
  tone = 'danger',
  isConfirming = false,
  onConfirm,
  onClose,
}: ConfirmationModalProps) {
  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isConfirming) onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isConfirming, isOpen, onClose])

  if (!isOpen) return null

  return createPortal(
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

        <div className={`${styles.iconWrap} ${tone === 'ai' ? styles.aiIconWrap : ''}`} aria-hidden="true">
          {tone === 'ai' ? <HiOutlineSparkles /> : <FiAlertTriangle />}
        </div>

        <div className={styles.copy}>
          <p className={styles.kicker}>{kicker}</p>
          <h2 id="confirm-delete-title">{title}</h2>
          <p id="confirm-delete-message">{message}</p>
        </div>

        <div className={styles.actions}>
          <button className={styles.cancelButton} type="button" onClick={onClose} disabled={isConfirming}>
            {cancelLabel}
          </button>
          <button
            className={`${styles.confirmButton} ${tone === 'ai' ? styles.aiConfirmButton : ''}`}
            type="button"
            onClick={onConfirm}
            disabled={isConfirming}
            autoFocus
          >
            {isConfirming ? workingLabel : confirmLabel}
          </button>
        </div>
      </section>
    </div>,
    document.body,
  )
}
